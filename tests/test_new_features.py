"""
Tests for the settings, engine, credential-storage, details, events, registry, system and stats
features. Like test_buttons.py they need no Docker daemon: docker is mocked where it is reached.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.test_buttons import _Base, _TableFixture, _F_CONTAINER, _F_IMAGE, FAKE_PW

from src.config import config_manager as cm


class _ConfigDir(unittest.TestCase):
    """Points the config manager at a throw-away directory."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self._patches = [patch.object(cm, "CONFIG_DIR", self.dir),
                         patch.object(cm, "CONFIG_FILE", self.dir / "config.json")]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def file_config(self):
        path = self.dir / "config.json"
        return json.loads(path.read_text()) if path.exists() else {}


# ===========================================================================
# Settings
# ===========================================================================

class TestSettings(_ConfigDir):

    def test_defaults_when_nothing_is_saved(self):
        for key, default in cm.DEFAULT_SETTINGS.items():
            self.assertEqual(cm.get_setting(key), default)

    def test_round_trip_keeps_other_config(self):
        cm.save_selected_theme("darkly")
        cm.set_setting("stats_interval", 5)
        cm.set_setting("engine", "podman")
        self.assertEqual(cm.get_setting("stats_interval"), 5)
        self.assertEqual(cm.get_setting("engine"), "podman")
        self.assertEqual(cm.load_selected_theme(), "darkly")

    def test_wrong_type_falls_back_to_default(self):
        (self.dir / "config.json").write_text(json.dumps({"settings": {"stats_interval": "fast",
                                                                       "notifications": 3}}))
        self.assertEqual(cm.get_setting("stats_interval"), cm.DEFAULT_SETTINGS["stats_interval"])
        self.assertEqual(cm.get_setting("notifications"), cm.DEFAULT_SETTINGS["notifications"])

    def test_unknown_key_is_rejected(self):
        with self.assertRaises(KeyError):
            cm.set_setting("nonsense", 1)


# ===========================================================================
# Password storage: keyring first, 0600 file as the fallback
# ===========================================================================

class TestPasswordStorage(_ConfigDir):

    def _keyring(self, store):
        """A fake `secret-tool`: lookup / store / clear against the `store` dict."""
        def run(args, input=None, **_kwargs):
            action = args[1]
            if action == "store":
                store["pw"] = input
                return MagicMock(returncode=0, stdout="")
            if action == "lookup":
                return MagicMock(returncode=0 if "pw" in store else 1, stdout=store.get("pw", ""))
            store.pop("pw", None)
            return MagicMock(returncode=0, stdout="")
        return patch.object(cm.subprocess, "run", side_effect=run)

    def test_saved_in_keyring_not_in_file(self):
        store = {}
        with patch.object(cm.shutil, "which", return_value="/usr/bin/secret-tool"), self._keyring(store):
            cm.save_password("s3cret")
            self.assertEqual(store["pw"], "s3cret")
            self.assertNotIn("password", self.file_config())
            self.assertEqual(cm.load_saved_password(), "s3cret")
            self.assertEqual(cm.password_storage(), "keyring")

    def test_file_fallback_without_secret_tool(self):
        with patch.object(cm.shutil, "which", return_value=None):
            cm.save_password("s3cret")
            self.assertEqual(self.file_config()["password"], "s3cret")
            self.assertEqual(cm.load_saved_password(), "s3cret")
            self.assertEqual(cm.password_storage(), "file")
        mode = (self.dir / "config.json").stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_legacy_file_password_moves_to_keyring(self):
        (self.dir / "config.json").write_text(json.dumps({"password": "old", "theme": "darkly"}))
        store = {}
        with patch.object(cm.shutil, "which", return_value="/usr/bin/secret-tool"), self._keyring(store):
            self.assertEqual(cm.load_saved_password(), "old")
        self.assertEqual(store["pw"], "old")
        self.assertEqual(self.file_config(), {"theme": "darkly"})

    def test_locked_keyring_falls_back_to_file(self):
        failing = MagicMock(returncode=1, stdout="")
        with patch.object(cm.shutil, "which", return_value="/usr/bin/secret-tool"), \
                patch.object(cm.subprocess, "run", return_value=failing):
            cm.save_password("s3cret")
        self.assertEqual(self.file_config()["password"], "s3cret")

    def test_delete_clears_keyring_and_file(self):
        store = {"pw": "x"}
        (self.dir / "config.json").write_text(json.dumps({"password": "x"}))
        with patch.object(cm.shutil, "which", return_value="/usr/bin/secret-tool"), self._keyring(store):
            cm.delete_saved_password()
            self.assertNotIn("pw", store)
        self.assertFalse((self.dir / "config.json").exists())


# ===========================================================================
# Command execution: engine swap, stdin input, sudo detection, notifications
# ===========================================================================

class TestEngine(unittest.TestCase):

    def _apply(self, cmd, engine):
        from src.utils.utils import apply_engine
        with patch("src.utils.utils.get_setting", return_value=engine):
            return apply_engine(cmd)

    def test_docker_is_left_alone(self):
        self.assertEqual(self._apply("docker ps -q", "docker"), "docker ps -q")

    def test_podman_replaces_each_command_position(self):
        self.assertEqual(self._apply("docker ps -q", "podman"), "podman ps -q")
        self.assertEqual(self._apply("docker stop $(docker ps -aq) 2>/dev/null || true", "podman"),
                         "podman stop $(podman ps -aq) 2>/dev/null || true")
        self.assertEqual(self._apply("docker rm a && docker rm b", "podman"), "podman rm a && podman rm b")

    def test_arguments_and_services_are_not_touched(self):
        self.assertEqual(self._apply("docker pull docker.io/library/docker", "podman"),
                         "podman pull docker.io/library/docker")
        self.assertEqual(self._apply("systemctl start docker.socket docker.service", "podman"),
                         "systemctl start docker.socket docker.service")

    def test_podman_has_no_daemon_to_check(self):
        from src.utils.utils import is_docker_running
        with patch("src.utils.utils.get_setting", return_value="podman"), \
                patch("src.utils.utils.subprocess.run") as run:
            self.assertTrue(is_docker_running())
            run.assert_not_called()

    def test_run_cmd_runs_the_configured_engine(self):
        from src.utils.utils import run_cmd
        with patch("src.utils.utils.get_setting", return_value="podman"), \
                patch("src.utils.utils.subprocess.check_output", return_value="ok\n") as out:
            run_cmd("docker ps")
        self.assertEqual(out.call_args[0][0], "podman ps")


class TestRunCmdInput(unittest.TestCase):

    def test_input_reaches_stdin_without_sudo(self):
        from src.utils.utils import run_cmd
        self.assertEqual(run_cmd("cat", input_text="hello"), "hello")

    def test_input_follows_the_sudo_password(self):
        from src.utils.utils import run_cmd
        process = MagicMock()
        process.communicate.return_value = ("Login Succeeded\n", "")
        with patch("src.utils.utils.subprocess.Popen", return_value=process) as popen:
            result = run_cmd("docker login -u me --password-stdin", sudo=True,
                             sudo_password=FAKE_PW, input_text="token\n")
        self.assertEqual(result, "Login Succeeded")
        self.assertTrue(popen.call_args[0][0].startswith("sudo -S docker login"))
        self.assertEqual(process.communicate.call_args.kwargs["input"], f"{FAKE_PW}\ntoken\n")


class TestSudoDetection(unittest.TestCase):

    def test_no_sudo_needed_when_docker_answers(self):
        from src.utils.utils import docker_needs_sudo
        with patch("src.utils.utils.subprocess.run", return_value=MagicMock(returncode=0, stdout="29.1.3\n")):
            self.assertFalse(docker_needs_sudo())

    def test_sudo_needed_on_permission_denied(self):
        from src.utils.utils import docker_needs_sudo
        with patch("src.utils.utils.subprocess.run", return_value=MagicMock(returncode=1, stdout="")):
            self.assertTrue(docker_needs_sudo())

    def test_sudo_needed_when_the_cli_hangs(self):
        import subprocess
        from src.utils.utils import docker_needs_sudo
        with patch("src.utils.utils.subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 15)):
            self.assertTrue(docker_needs_sudo())


class TestNotify(unittest.TestCase):

    def _notify(self, *, enabled=True, tool="/usr/bin/notify-send", root=None):
        from src.utils.utils import notify
        with patch("src.utils.utils.get_setting", return_value=enabled), \
                patch("src.utils.utils.shutil.which", return_value=tool), \
                patch("src.utils.utils.subprocess.Popen") as popen:
            return notify("Build", "done", root), popen

    def test_sends_when_enabled(self):
        sent, popen = self._notify()
        self.assertTrue(sent)
        self.assertEqual(popen.call_args[0][0][-2:], ["Build", "done"])

    def test_silent_when_disabled_or_tool_missing(self):
        self.assertFalse(self._notify(enabled=False)[0])
        self.assertFalse(self._notify(tool=None)[0])

    def test_skipped_while_the_window_has_focus(self):
        root = MagicMock()
        root.focus_displayof.return_value = object()
        sent, popen = self._notify(root=root)
        self.assertFalse(sent)
        popen.assert_not_called()

    def test_sent_when_the_window_is_in_the_background(self):
        root = MagicMock()
        root.focus_displayof.return_value = None
        self.assertTrue(self._notify(root=root)[0])

    def test_finished_stream_session_notifies(self):
        from src.shared import stream
        root = MagicMock()
        root.after.side_effect = lambda _ms, fn: fn()
        captured = {}

        def fake_stream(command, sudo, sudo_password, output_callback, complete_callback):
            captured["complete"] = complete_callback
            return {}

        with patch.object(stream, "stream_docker_cmd", side_effect=fake_stream), \
                patch.object(stream, "notify") as notify:
            stream._start_stream_session(root, "Pull — nginx", "docker pull nginx")
            captured["complete"]("done", 0, False)
        notify.assert_called_once()
        self.assertEqual(notify.call_args[0][:2], ("Pull — nginx", "Completed successfully"))


class TestTerminalChoice(unittest.TestCase):

    def test_chosen_terminal_wins_when_installed(self):
        from src.utils.utils import check_terminal_installed
        with patch("src.utils.utils.installed_terminals", return_value=["tilix", "xterm"]), \
                patch("src.utils.utils.get_setting", return_value="xterm"):
            self.assertEqual(check_terminal_installed(), "xterm")

    def test_missing_choice_falls_back_to_first_installed(self):
        from src.utils.utils import check_terminal_installed
        with patch("src.utils.utils.installed_terminals", return_value=["tilix"]), \
                patch("src.utils.utils.get_setting", return_value="konsole"):
            self.assertEqual(check_terminal_installed(), "tilix")
        with patch("src.utils.utils.installed_terminals", return_value=[]), \
                patch("src.utils.utils.get_setting", return_value="auto"):
            self.assertIsNone(check_terminal_installed())


# ===========================================================================
# Command constants
# ===========================================================================

class TestNewCommandStrings(unittest.TestCase):

    def test_formats(self):
        from src.docker import commands as c
        self.assertEqual(c.DOCKER_CONTAINER_TOP.format(container="web"), "docker top web")
        self.assertEqual(c.DOCKER_CONTAINER_DIFF.format(container="web"), "docker diff web")
        self.assertEqual(c.DOCKER_CONTAINER_EXPORT.format(output_file="a.tar", container="web"),
                         "docker export -o a.tar web")
        self.assertEqual(c.DOCKER_IMAGE_IMPORT.format(input_file="a.tar", image="x:1"), "docker import a.tar x:1")
        self.assertEqual(c.DOCKER_CONTEXT_USE.format(context="remote"), "docker context use remote")
        self.assertEqual(c.DOCKER_CONTAINER_LOGS_FOLLOW.format(timestamps_flag="--timestamps", lines="50",
                                                              container="web"),
                         "docker logs --timestamps --tail 50 --follow web")
        self.assertEqual(c.DOCKER_COMPOSE_LOGS_FOLLOW.format(files="-f a.yml", lines="200"),
                         "docker compose -f a.yml logs --tail 200 --follow")
        self.assertEqual(c.DOCKER_LOGIN.format(username="me", registry=" ghcr.io"),
                         "docker login -u me --password-stdin ghcr.io")
        self.assertEqual(c.DOCKER_LOGIN.format(username="me", registry=""), "docker login -u me --password-stdin")
        self.assertEqual(c.DOCKER_LOGOUT.format(registry=""), "docker logout")

    def test_password_is_never_part_of_the_login_command(self):
        from src.docker.commands import DOCKER_LOGIN
        self.assertIn("--password-stdin", DOCKER_LOGIN)
        self.assertNotIn("--password ", DOCKER_LOGIN)
        self.assertNotIn("{password}", DOCKER_LOGIN)


# ===========================================================================
# Container details
# ===========================================================================

_INSPECT = json.dumps([{
    "Id": "9bd0d8d73572aa97", "Name": "/web", "Created": "2026-10-14T07:40:02Z", "RestartCount": 3,
    "State": {"Status": "running", "ExitCode": 0, "OOMKilled": False, "StartedAt": "2026-10-14T07:40:12Z",
              "FinishedAt": "0001-01-01T00:00:00Z",
              "Health": {"Status": "unhealthy", "FailingStreak": 4,
                         "Log": [{"ExitCode": 1, "End": "2026-10-14T08:00:00Z", "Output": "curl: refused\nmore"}]}},
    "Config": {"Image": "nginx:1", "Entrypoint": ["/entry"], "Cmd": ["serve"],
               "Env": ["MODE=prod", "DB_PASSWORD=hunter2", "API_TOKEN=abc", "EMPTY_SECRET="]},
    "HostConfig": {"RestartPolicy": {"Name": "on-failure", "MaximumRetryCount": 5}},
    "NetworkSettings": {"Ports": {"80/tcp": [{"HostIp": "", "HostPort": "8080"}], "443/tcp": None},
                        "Networks": {"bridge": {"IPAddress": "172.17.0.2"}}},
    "Mounts": [{"Type": "volume", "Name": "data", "Destination": "/var/lib/data", "RW": True},
               {"Type": "bind", "Source": "/etc/conf", "Destination": "/conf", "RW": False}],
}])


class TestContainerDetails(unittest.TestCase):

    def setUp(self):
        from src.containers.details import format_container_details
        self.text = format_container_details(_INSPECT)

    def test_summary_and_state(self):
        self.assertIn("Container   web  (9bd0d8d73572)", self.text)
        self.assertIn("Command     /entry serve", self.text)
        self.assertIn("running (unhealthy)", self.text)
        self.assertIn("Restarts      3   (policy: on-failure:5)", self.text)
        self.assertIn("OOM killed    no", self.text)
        self.assertIn("Finished      —", self.text)

    def test_health_ports_networks_mounts(self):
        self.assertIn("Failing streak   4", self.text)
        self.assertIn("Output           curl: refused", self.text)
        self.assertNotIn("more", self.text)
        self.assertIn("80/tcp  →  0.0.0.0:8080", self.text)
        self.assertIn("443/tcp  (not published)", self.text)
        self.assertIn("bridge", self.text)
        self.assertIn("172.17.0.2", self.text)
        self.assertIn("data  →  /var/lib/data  (rw)", self.text)
        self.assertIn("/etc/conf  →  /conf  (ro)", self.text)

    def test_secret_environment_values_are_hidden(self):
        self.assertIn("MODE=prod", self.text)
        self.assertIn("DB_PASSWORD=••••••••", self.text)
        self.assertIn("API_TOKEN=••••••••", self.text)
        self.assertNotIn("hunter2", self.text)
        self.assertIn("EMPTY_SECRET=", self.text)

    def test_non_inspect_output_is_returned_unchanged(self):
        from src.containers.details import format_container_details
        for text in ("Error response from daemon: No such container: x", "", "[]", "{}"):
            self.assertEqual(format_container_details(text), text)


# ===========================================================================
# Row actions added by this change
# ===========================================================================

class TestNewRowActions(_Base):

    def setUp(self):
        super().setUp()
        self._patch = patch('src.shared.item_actions.check_docker_running', return_value=True)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        super().tearDown()

    def _build(self, table_type, row):
        from src.shared.item_actions import create_selected_item_actions
        dm = MagicMock()
        dm.get_selected_items.return_value = [MagicMock()]
        dm.get_item_values.return_value = row
        dm.current_table_type = table_type
        buttons, _ = create_selected_item_actions(ttk_frame(self.root), self.root, dm, MagicMock(), MagicMock())
        return buttons, dm

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_details_runs_inspect_and_formats_the_result(self, run):
        buttons, dm = self._build('container', _F_CONTAINER)
        buttons['details'].invoke()
        self.assertEqual(run.call_args[0][0], "docker inspect c1a2b3c4d5e6")
        run.call_args.kwargs['callback'](_INSPECT)
        shown = dm.show_text_output.call_args[0][0]
        self.assertTrue(shown.startswith("Container Details - mycontainer"))
        self.assertIn("running (unhealthy)", shown)

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_top_and_diff(self, run):
        buttons, dm = self._build('container', _F_CONTAINER)
        buttons['top'].invoke()
        self.assertEqual(run.call_args[0][0], "docker top c1a2b3c4d5e6")
        buttons['diff'].invoke()
        self.assertEqual(run.call_args[0][0], "docker diff c1a2b3c4d5e6")
        run.call_args.kwargs['callback']("")
        self.assertIn("No changes", dm.show_text_output.call_args[0][0])

    @patch('src.shared.item_actions.run_docker_cmd')
    @patch('src.shared.item_actions.filedialog.asksaveasfilename', return_value="/tmp/web export.tar")
    def test_export_quotes_the_path(self, _dialog, run):
        buttons, _dm = self._build('container', _F_CONTAINER)
        buttons['export'].invoke()
        self.assertEqual(run.call_args[0][0], "docker export -o '/tmp/web export.tar' c1a2b3c4d5e6")

    @patch('src.shared.item_actions.run_docker_cmd')
    @patch('src.shared.item_actions.filedialog.asksaveasfilename', return_value="")
    def test_export_cancelled_runs_nothing(self, _dialog, run):
        buttons, _dm = self._build('container', _F_CONTAINER)
        buttons['export'].invoke()
        run.assert_not_called()

    @patch('src.images.dialogs.scan_image')
    def test_scan_passes_the_image_reference(self, scan):
        buttons, _dm = self._build('image', _F_IMAGE)
        buttons['scan_image'].invoke()
        self.assertEqual(scan.call_args[0][1], "nginx:latest")

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_context_use_and_inspect(self, run):
        row = (1, 'remote', 'ssh host', 'ssh://me@host', 'false')
        buttons, _dm = self._build('context', row)
        buttons['use_context'].invoke()
        self.assertEqual(run.call_args[0][0], "docker context use remote")
        buttons['inspect_context'].invoke()
        self.assertEqual(run.call_args[0][0], "docker context inspect remote")

    @patch('src.containers.dialogs.show_logs_window')
    def test_compose_logs_open_the_shared_viewer_with_follow(self, viewer):
        buttons, _dm = self._build('compose', (1, 'myapp', 'running', '/app/docker-compose.yml'))
        buttons['compose_logs'].invoke()
        args, kwargs = viewer.call_args
        fetch, follow = args[3], args[4]
        self.assertEqual(fetch("100", ""), "docker compose -f /app/docker-compose.yml logs --tail 100")
        self.assertEqual(follow("100", ""), "docker compose -f /app/docker-compose.yml logs --tail 100 --follow")
        self.assertFalse(kwargs["timestamps"])

    def test_action_layout_offers_the_new_buttons(self):
        from src.ui.ui_display import DisplayManager as DM
        for table in ('container', 'container_stats'):
            for name in ('details', 'top'):
                self.assertIn(name, DM._ACTION_LAYOUT[table])
        self.assertEqual(DM._ACTION_LAYOUT['context'], ['use_context', 'inspect_context'])
        for name in ('details', 'top', 'diff', 'export', 'scan_image', 'use_context', 'inspect_context'):
            self.assertIn(name, DM._SINGLE_ROW_ACTIONS)


def ttk_frame(root):
    from tkinter import ttk
    return ttk.Frame(root)


# ===========================================================================
# Row colouring
# ===========================================================================

class TestStatusTone(unittest.TestCase):

    def test_tones(self):
        from src.ui.cell_format import status_tone
        cases = {
            "Up 2 hours": None,
            "Up 2 hours (healthy)": "ok",
            "Up 2 hours (unhealthy)": "bad",
            "Restarting (1) 5 seconds ago": "bad",
            "Dead": "bad",
            "Exited (0) 3 days ago": None,
            "Exited (137) 30 hours ago": "warn",
            "Up 1 hour (Paused)": "warn",
            "": None,
        }
        for text, tone in cases.items():
            self.assertEqual(status_tone(text), tone, text)


class TestRowTags(_TableFixture):

    def test_rows_carry_their_status_tone(self):
        rows = self.ROWS + [["c4", "api", "x", "Up 1 hour (unhealthy)", "", "4B"],
                            ["c5", "job", "x", "Exited (1) 2 days ago", "", "5B"]]
        self.dm.show_table(self.COLS, rows, 'container', "All Containers")
        tags = {self.tree.item(i)['values'][2]: self.tree.item(i)['tags'] for i in self.tree.get_children()}
        self.assertNotIn("status_bad", tags["web"])
        self.assertIn("status_warn", tags["cache"])      # paused
        self.assertIn("status_bad", tags["api"])         # unhealthy
        self.assertIn("status_warn", tags["job"])        # exited with an error code
        self.assertNotIn("status_warn", tags["db"])      # exited cleanly

    def test_tables_without_a_status_column_have_no_tones(self):
        self.dm.show_table(["NAME", "SIZE"], [["a", "1B"]], 'volume', "Volumes")
        for i in self.tree.get_children():
            self.assertEqual([t for t in self.tree.item(i)['tags'] if t.startswith("status_")], [])


# ===========================================================================
# Stats: trends and refresh interval
# ===========================================================================

class TestSparkline(unittest.TestCase):

    def test_scaling(self):
        from src.stats.tables import sparkline
        self.assertEqual(sparkline([]), "")
        self.assertEqual(sparkline([0, 1, 2, 3, 4, 5, 6, 7]), "▁▂▃▄▅▆▇█")
        self.assertEqual(sparkline([0, 0, 0]), "▁▁▁")          # idle: flat, not a divide by zero
        self.assertEqual(sparkline([10, 50, 100], top=100), "▂▅█")


class TestStatsTrends(unittest.TestCase):

    def setUp(self):
        from src.stats import tables
        self.tables = tables
        tables._history.clear()

    def _row(self, cpu, mem="10%", cid="abc"):
        return [cid, "web", cpu, "1MiB / 2GiB", mem, "0B / 0B", "0B / 0B", "3"]

    def test_history_builds_up_and_drops_removed_containers(self):
        first = self.tables._with_trends([self._row("1%"), self._row("5%", cid="old")])
        self.assertEqual(len(first[0]), len(self.tables._COLUMNS))
        self.tables._with_trends([self._row("40%")])
        self.assertEqual(set(self.tables._history), {"abc"})
        rows = self.tables._with_trends([self._row("90%")])
        self.assertEqual(len(rows[0][-2]), 3)                  # three samples so far
        self.assertEqual(rows[0][-2][-1], "█")                 # newest is the peak

    def test_history_is_capped(self):
        for _ in range(self.tables._HISTORY_LEN + 10):
            rows = self.tables._with_trends([self._row("2%")])
        self.assertEqual(len(rows[0][-2]), self.tables._HISTORY_LEN)

    def test_unparsable_percentages_are_skipped(self):
        rows = self.tables._with_trends([self._row("--", mem="--")])
        self.assertEqual(rows[0][-2:], ["", ""])

    @patch('src.stats.tables.get_setting', return_value=7)
    def test_refresh_interval_comes_from_settings(self, _get):
        self.assertEqual(self.tables._interval_ms(), 7000)


class TestStatsControls(_Base):

    def test_interval_button_cycles_and_saves(self):
        from tkinter import ttk
        from src.stats import tables
        frame = ttk.Frame(self.root)
        dm = MagicMock()
        dm.action_frame = frame
        dm.live_stats_enabled = False
        saved = {"stats_interval": 2}
        with patch.object(tables, "check_docker_running", return_value=True), \
                patch.object(tables, "run_cmd", return_value=""), \
                patch.object(tables, "get_setting", side_effect=lambda key: saved[key]), \
                patch.object(tables, "set_setting", side_effect=lambda key, value: saved.update({key: value})):
            tables.show_containers_with_stats(MagicMock(), MagicMock(), dm)
            button = next(w for w in frame.winfo_children() if "⏱" in str(w.cget("text")))
            self.assertEqual(button.cget("text"), "⏱ 2s")
            button.invoke()
            self.assertEqual((saved["stats_interval"], button.cget("text")), (3, "⏱ 3s"))
            for _ in range(len(tables._INTERVALS)):
                button.invoke()
            self.assertEqual(saved["stats_interval"], 3)       # full cycle returns to the start


# ===========================================================================
# Events window
# ===========================================================================

class TestEvents(unittest.TestCase):

    def test_tone(self):
        from src.system.dialogs import event_tone
        self.assertEqual(event_tone("oom"), "bad")
        self.assertEqual(event_tone("kill"), "bad")
        self.assertEqual(event_tone("health_status: unhealthy"), "bad")
        self.assertEqual(event_tone("die"), "warn")
        self.assertEqual(event_tone("start"), "ok")
        self.assertEqual(event_tone("health_status: healthy"), "ok")
        self.assertIsNone(event_tone("create"))

    def test_format_event_line(self):
        from src.system.dialogs import format_event
        text, tone = format_event("1792085375\tcontainer\tdie\tabcdef1234567890\tweb\n")
        self.assertRegex(text, r"^\d\d:\d\d:\d\d  container +die +web$")
        self.assertEqual(tone, "warn")

    def test_unnamed_actors_fall_back_to_their_id(self):
        from src.system.dialogs import format_event
        text, _tone = format_event("1792085375\tvolume\tcreate\tmy-volume\t<no value>")
        self.assertTrue(text.endswith("my-volume"))

    def test_unexpected_lines_are_shown_as_they_are(self):
        from src.system.dialogs import format_event
        self.assertEqual(format_event("Error: permission denied\n"), ("Error: permission denied", None))

    def test_command(self):
        from src.system.dialogs import events_command
        self.assertTrue(events_command("all", "10m").startswith("docker events --since 10m --format"))
        self.assertIn("--since 0s --filter type=volume --format", events_command("volume", "0s"))


# ===========================================================================
# Registry login, scanning, import
# ===========================================================================

class TestRegistryHelpers(unittest.TestCase):

    def test_parse_registries(self):
        from src.images.dialogs import parse_registries
        config = json.dumps({"auths": {"ghcr.io": {}, "https://index.docker.io/v1/": {},
                                       "https://index.docker.io/v1/access-token": {}}})
        self.assertEqual(parse_registries(config), ["ghcr.io", "https://index.docker.io/v1/"])
        for bad in ("", "not json", "[]", '{"auths": []}', "{}"):
            self.assertEqual(parse_registries(bad), [], bad)

    def test_scanner_detection(self):
        from src.images.dialogs import _scanner_missing
        self.assertTrue(_scanner_missing("docker: unknown command: docker scout"))
        self.assertTrue(_scanner_missing("sh: 1: trivy: not found"))
        self.assertFalse(_scanner_missing("2 vulnerabilities found"))


class TestRegistryDialog(_Base):

    def _open(self, config_text='{"auths": {"ghcr.io": {}}}'):
        from src.images import dialogs
        calls = []

        def fake_run(cmd, sudo=False, sudo_password=None, input_text=None):
            calls.append((cmd, input_text))
            return config_text if cmd.startswith("sh -c") else "Login Succeeded"

        patches = [patch.object(dialogs, "check_docker_running", return_value=True),
                   patch.object(dialogs, "run_cmd", side_effect=fake_run),
                   patch.object(dialogs, "get_sudo_password", return_value=FAKE_PW),
                   patch.object(dialogs, "startThreadForTask", side_effect=lambda fn: fn())]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        dialogs.registry_dialog(self.root)
        dialog = [w for w in self.root.winfo_children() if w.winfo_class() == "Toplevel"][-1]
        return dialog, calls

    def _find(self, widget, cls):
        found = []
        for child in widget.winfo_children():
            if child.winfo_class() == cls:
                found.append(child)
            found += self._find(child, cls)
        return found

    def test_shows_where_the_user_is_logged_in(self):
        dialog, _calls = self._open()
        self.root.update()
        labels = [str(w.cget("text")) for w in self._find(dialog, "TLabel")]
        self.assertIn("Logged in to: ghcr.io", labels)

    def test_login_sends_the_password_on_stdin_only(self):
        dialog, calls = self._open()
        entries = self._find(dialog, "TEntry")
        combo = self._find(dialog, "TCombobox")[0]
        combo.set("ghcr.io")
        user, password = entries[-2], entries[-1]
        user.insert(0, "me")
        password.insert(0, "tok en")
        next(b for b in self._find(dialog, "TButton") if b.cget("text") == "Login").invoke()
        self.root.update()                                     # run the dialog's after() callbacks
        command, stdin = next(c for c in calls if c[0].startswith("docker login"))
        self.assertEqual(command, "docker login -u me --password-stdin ghcr.io")
        self.assertEqual(stdin, "tok en\n")
        self.assertNotIn("tok en", command)
        self.assertEqual(password.get(), "")                   # cleared after use

    def test_login_needs_both_fields(self):
        dialog, calls = self._open()
        with patch("src.images.dialogs.messagebox.showwarning") as warn:
            next(b for b in self._find(dialog, "TButton") if b.cget("text") == "Login").invoke()
        warn.assert_called_once()
        self.assertFalse([c for c in calls if c[0].startswith("docker login")])

    def test_logout_command(self):
        dialog, calls = self._open()
        self._find(dialog, "TCombobox")[0].set("ghcr.io")
        next(b for b in self._find(dialog, "TButton") if b.cget("text") == "Logout").invoke()
        self.root.update()
        self.assertIn(("docker logout ghcr.io", None), calls)


class TestPushHelpers(unittest.TestCase):

    def test_hub_references_need_a_username(self):
        from src.images.dialogs import needs_hub_namespace
        for image in ("nginx", "app:1", "library/nginx", "docker.io/library/app:1", "index.docker.io/app"):
            self.assertTrue(needs_hub_namespace(image), image)
        for image in ("me/app:1", "docker.io/me/app", "ghcr.io/me/app", "localhost:5000/app", "reg.example.com/app"):
            self.assertFalse(needs_hub_namespace(image), image)

    def test_push_target(self):
        from src.images.dialogs import _push_target
        self.assertEqual(_push_target("app:1", "me"), "me/app:1")
        self.assertEqual(_push_target("docker.io/library/app:1", "me"), "me/app:1")

    def test_error_summary_shows_the_reason_not_the_layer_noise(self):
        from src.images.dialogs import push_error_summary
        output = ("The push refers to repository [docker.io/library/x]\n"
                  + "".join(f"{i:012x}: Waiting\n" for i in range(30))
                  + "push access denied, repository does not exist: insufficient_scope: authorization failed")
        summary = push_error_summary(output)
        self.assertNotIn("Waiting", summary)
        self.assertIn("insufficient_scope", summary)

    def test_success_needs_the_final_digest_line(self):
        from src.images.dialogs import _PUSH_OK
        self.assertTrue(_PUSH_OK.search("1: digest: sha256:abc123 size: 1234"))
        self.assertFalse(_PUSH_OK.search("abc: Layer already exists\ndenied: requested access to the resource is denied"))


class TestPushDialog(_Base):

    def _push(self, image, outputs, username="MyUser"):
        from src.images import dialogs
        commands = []

        def fake_run(cmd, sudo=False, sudo_password=None, **_kw):
            commands.append(cmd)
            return outputs.pop(0)

        patches = [patch.object(dialogs, "check_docker_running", return_value=True),
                   patch.object(dialogs, "run_cmd", side_effect=fake_run),
                   patch.object(dialogs, "get_sudo_password", return_value=None),
                   patch.object(dialogs, "startThreadForTask", side_effect=lambda fn: fn()),
                   patch.object(dialogs.simpledialog, "askstring", return_value=username)]
        mocks = [p.start() for p in patches]
        self.addCleanup(lambda: [p.stop() for p in patches])
        with patch.object(dialogs.messagebox, "showerror") as error:
            dialogs.push_image_dialog(self.root, image_ref=image)
            dialog = [w for w in self.root.winfo_children() if w.winfo_class() == "Toplevel"][-1]
            next(b for b in _walk(dialog) if b.winfo_class() == "TButton" and b.cget("text") == "Push").invoke()
            self.root.update()
        return commands, mocks[-1], error

    def test_image_without_username_is_tagged_then_pushed(self):
        commands, ask, _error = self._push("app:1", ["", "1: digest: sha256:abc size: 10"])
        ask.assert_called_once()
        self.assertEqual(commands, ["docker tag app:1 myuser/app:1", "docker push myuser/app:1"])

    def test_cancelling_the_username_prompt_pushes_nothing(self):
        commands, _ask, _error = self._push("app:1", [], username=None)
        self.assertEqual(commands, [])

    def test_namespaced_image_is_pushed_as_it_is(self):
        commands, ask, _error = self._push("me/app:1", ["1: digest: sha256:abc size: 10"])
        ask.assert_not_called()
        self.assertEqual(commands, ["docker push me/app:1"])

    def test_denied_push_shows_the_reason_and_a_hint(self):
        out = "x: Waiting\n" * 25 + "denied: requested access to the resource is denied"
        _commands, _ask, error = self._push("me/app:1", [out])
        message = error.call_args[0][1]
        self.assertIn("requested access to the resource is denied", message)
        self.assertIn("Docker Hub username", message)
        self.assertNotIn("Waiting", message)


class TestScanImage(_Base):

    def _scan(self, outputs):
        from src.images import dialogs
        shown, commands = [], []

        def fake_run(cmd, sudo=False, sudo_password=None, **_kw):
            commands.append(cmd)
            return outputs[len(commands) - 1]

        self.root.after = lambda _ms, fn: fn()
        with patch.object(dialogs, "check_docker_running", return_value=True), \
                patch.object(dialogs, "run_cmd", side_effect=fake_run), \
                patch.object(dialogs, "startThreadForTask", side_effect=lambda fn: fn()):
            dialogs.scan_image(self.root, "nginx:1", shown.append)
        return shown[0], commands

    def test_uses_scout_when_available(self):
        text, commands = self._scan(["CVE-1 high"])
        self.assertEqual(commands, ["docker scout cves nginx:1"])
        self.assertIn("(docker scout)", text)

    def test_falls_back_to_trivy(self):
        text, commands = self._scan(["docker: unknown command: docker scout", "Total: 3"])
        self.assertEqual(commands[-1], "trivy image nginx:1")
        self.assertIn("(trivy)", text)

    def test_explains_when_no_scanner_is_installed(self):
        text, _commands = self._scan(["docker: unknown command: docker scout", "sh: 1: trivy: not found"])
        self.assertIn("No vulnerability scanner is installed", text)


class TestImagesAndBuild(_Base):

    @patch('src.images.tables.check_docker_running', return_value=True)
    @patch('src.images.tables.show_table_command')
    def test_dangling_view(self, cmd, _running):
        from src.images.tables import show_dangling_images
        show_dangling_images(MagicMock(), MagicMock())
        self.assertIn("dangling=true", cmd.call_args[0][0])
        self.assertEqual(cmd.call_args.kwargs["table_type"], "image")

    @patch('src.images.dialogs.check_docker_running', return_value=True)
    @patch('src.images.dialogs.run_docker_cmd')
    @patch('src.images.dialogs.simpledialog.askstring', return_value="app:imported")
    @patch('src.images.dialogs.filedialog.askopenfilename', return_value="/tmp/my app.tar")
    def test_import_image(self, _file, _name, run, _running):
        from src.images.dialogs import import_image_dialog
        import_image_dialog(self.root, MagicMock())
        self.assertEqual(run.call_args[0][0], "docker import '/tmp/my app.tar' app:imported")

    @patch('src.images.dialogs.check_docker_running', return_value=True)
    @patch('src.images.dialogs.run_docker_cmd')
    @patch('src.images.dialogs.simpledialog.askstring', return_value=None)
    @patch('src.images.dialogs.filedialog.askopenfilename', return_value="/tmp/a.tar")
    def test_import_needs_an_image_name(self, _file, _name, run, _running):
        from src.images.dialogs import import_image_dialog
        import_image_dialog(self.root, MagicMock())
        run.assert_not_called()

    @patch('src.images.dialogs.check_docker_running', return_value=True)
    @patch('src.images.dialogs.get_sudo_password', return_value=FAKE_PW)
    def test_build_platform_is_added_before_build_args(self, _pw, _running):
        from tkinter import ttk
        from src.images import dialogs
        started = {}
        with patch.object(dialogs, "_start_stream_session",
                          side_effect=lambda *a, **k: started.update(command=a[2]) or {}), \
                patch.object(dialogs, "_show_stream_session_window", return_value=self.root):
            dialogs.build_image_dialog(self.root, MagicMock())
            dialog = [w for w in self.root.winfo_children() if w.winfo_class() == "Toplevel"][-1]
            entries = [w for w in _walk(dialog) if w.winfo_class() == "TEntry"]
            entries[0].insert(0, "app:1")
            entries[1].insert(0, "/src/app")
            entries[3].insert(0, "linux/arm64")
            text = next(w for w in _walk(dialog) if w.winfo_class() == "Text")
            text.insert("1.0", "VERSION=2")
            next(b for b in _walk(dialog) if isinstance(b, ttk.Button) and b.cget("text") == "Build").invoke()
        self.assertEqual(started["command"],
                         "docker build -t app:1 --platform linux/arm64 --build-arg VERSION=2 /src/app")


def _walk(widget):
    for child in widget.winfo_children():
        yield child
        yield from _walk(child)


# ===========================================================================
# System category
# ===========================================================================

class TestSystemCategory(_Base):

    def test_menu_has_the_system_buttons(self):
        from src.config.config_menu import get_menu_structure, VIEW_BUTTONS
        menu = get_menu_structure(*[MagicMock() for _ in range(46)])
        self.assertEqual([label for label, _ in menu["System"]],
                         ["Info", "Contexts", "Events", "Builders", "Prune Build Cache"])
        self.assertIn("Dangling", [label for label, _ in menu["Images"]])
        self.assertIn("Registry", [label for label, _ in menu["Images"]])
        self.assertIn("Import", [label for label, _ in menu["Images"]])
        self.assertEqual(VIEW_BUTTONS["System"], {"Contexts"})
        self.assertIn("Dangling", VIEW_BUTTONS["Images"])

    def test_every_button_has_a_tooltip(self):
        from src.config.config_menu import get_menu_structure
        from src.config.config_tooltips import CATEGORY_TOOLTIPS, SIDEBAR_TOOLTIPS
        menu = get_menu_structure(*[MagicMock() for _ in range(46)])
        self.assertIn("System", SIDEBAR_TOOLTIPS)
        for category in ("System", "Images"):
            for label, _ in menu[category]:
                self.assertIn(label, CATEGORY_TOOLTIPS[category], f"{category}/{label}")

    @patch('src.system.actions.get_sudo_password', return_value=FAKE_PW)
    def test_info_shows_version_then_info(self, _pw):
        from src.system import actions
        shown = []
        outputs = {"docker version": "Client: 29", "docker info": "Server: ok"}
        with patch.object(actions, "async_run",
                          side_effect=lambda cmd, cb, **_kw: cb(outputs[cmd])):
            actions.show_system_info(shown.append)
        self.assertEqual(len(shown), 1)
        self.assertLess(shown[0].index("Client: 29"), shown[0].index("Server: ok"))

    @patch('src.system.actions.get_sudo_password', return_value=FAKE_PW)
    @patch('src.system.actions.check_docker_running', return_value=True)
    def test_builders_explain_a_missing_plugin(self, *_):
        from src.system import actions
        shown = []
        with patch.object(actions, "async_run",
                          side_effect=lambda cmd, cb, **_kw: cb("docker: unknown command: docker buildx")):
            actions.show_builders(shown.append)
        self.assertIn("buildx plugin is not installed", shown[0])

    @patch('src.system.actions.check_docker_running', return_value=True)
    @patch('src.system.actions.confirm_and_run')
    def test_prune_build_cache_asks_first(self, confirm, _running):
        from src.system import actions
        actions.prune_build_cache(MagicMock(), self.root, MagicMock())
        self.assertEqual(confirm.call_args[0][1], "docker builder prune -f")

    @patch('src.system.tables.show_table_command')
    def test_contexts_table_needs_no_local_daemon(self, cmd):
        from src.system.tables import show_contexts
        show_contexts(MagicMock(), MagicMock())
        self.assertEqual(cmd.call_args.kwargs["table_type"], "context")
        self.assertEqual(cmd.call_args[0][1], ["NAME", "DESCRIPTION", "DOCKER ENDPOINT", "CURRENT"])


# ===========================================================================
# Settings dialog
# ===========================================================================

class TestSettingsDialog(_ConfigDir, _Base):

    def setUp(self):
        _ConfigDir.setUp(self)
        _Base.setUp(self)

    def tearDown(self):
        _Base.tearDown(self)
        _ConfigDir.tearDown(self)

    def test_save_persists_every_choice(self):
        from tkinter import ttk
        from src.ui import settings_dialog as sd
        with patch.object(sd, "installed_terminals", return_value=["tilix", "xterm"]), \
                patch.object(sd, "docker_needs_sudo", return_value=False), \
                patch.object(sd.messagebox, "showinfo") as info:
            sd.settings_dialog(self.root)
            dialog = [w for w in self.root.winfo_children() if w.winfo_class() == "Toplevel"][-1]
            combos = [w for w in _walk(dialog) if isinstance(w, ttk.Combobox)]
            interval, engine, terminal = combos
            interval.set("5s")
            engine.set("podman")
            terminal.set("xterm")
            next(w for w in _walk(dialog) if w.winfo_class() == "TCheckbutton").invoke()   # notifications off
            next(b for b in _walk(dialog) if isinstance(b, ttk.Button) and b.cget("text") == "Save").invoke()
        self.assertEqual(cm.get_setting("stats_interval"), 5)
        self.assertEqual(cm.get_setting("engine"), "podman")
        self.assertEqual(cm.get_setting("terminal"), "xterm")
        self.assertFalse(cm.get_setting("notifications"))
        info.assert_called_once()                              # engine changed → relaunch hint


if __name__ == "__main__":
    unittest.main()
