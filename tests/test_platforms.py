"""
Tests for the cross-platform layer: the shell-free command parser used on Windows, Docker Desktop
service control (macOS / Windows), notifications, terminal launching and the no-sudo behaviour.

Platform switches are patched on `platform_utils`, so every OS branch is checked on any host.
"""

import collections
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from src.utils import platform_utils as plat, shell, terminals


def _as(os_name):
    """Patch the platform flags so the code believes it runs on `os_name`."""
    flags = {"linux": (True, False, False), "mac": (False, True, False), "win": (False, False, True)}
    linux, mac, win = flags[os_name]
    return [patch.object(plat, "IS_LINUX", linux), patch.object(plat, "IS_MAC", mac),
            patch.object(plat, "IS_WIN", win)]


class _OnPlatform(unittest.TestCase):
    platform = "linux"

    def setUp(self):
        for p in _as(self.platform):
            p.start()
            self.addCleanup(p.stop)


# ===========================================================================
# shell.parse — what Windows runs instead of `sh -c`
# ===========================================================================

class TestShellParse(unittest.TestCase):

    def test_plain_command_with_quoting(self):
        argv, discard = shell.parse("docker ps --format '{{.ID}}\t{{.Names}}'")
        self.assertEqual(argv, ["docker", "ps", "--format", "{{.ID}}\t{{.Names}}"])
        self.assertFalse(discard)

    def test_shlex_quote_round_trips_awkward_paths(self):
        import shlex
        path = r"C:\Users\Jo Smith\my 'file'.yml"
        argv, _ = shell.parse(f"docker compose -f {shlex.quote(path)} up -d")
        self.assertEqual(argv[-3], path)

    def test_stderr_redirect_and_ignore_failure_are_understood(self):
        with patch.object(shell.subprocess, "run", return_value=MagicMock(stdout="a1\nb2\n")):
            argv, discard = shell.parse("docker rmi -f $(docker images -aq) 2>/dev/null || true")
        self.assertEqual(argv, ["docker", "rmi", "-f", "a1", "b2"])
        self.assertTrue(discard)

    def test_substitution_runs_the_inner_command_without_a_shell(self):
        with patch.object(shell.subprocess, "run", return_value=MagicMock(stdout="x\n")) as run:
            shell.parse("docker start $(docker ps -aq)")
        self.assertEqual(run.call_args[0][0][1:], ["ps", "-aq"])
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_empty_substitution_drops_the_argument_like_sh_does(self):
        with patch.object(shell.subprocess, "run", return_value=MagicMock(stdout="")):
            argv, _ = shell.parse("docker stop $(docker ps -aq)")
        self.assertEqual(argv, ["docker", "stop"])

    def test_substitution_of_a_missing_program_is_empty(self):
        with patch.object(shell.subprocess, "run", side_effect=FileNotFoundError):
            argv, _ = shell.parse("docker stop $(docker ps -aq)")
        self.assertEqual(argv, ["docker", "stop"])

    def test_unsupported_shell_syntax_is_refused_not_misparsed(self):
        for cmd in ("docker ps | grep x", "docker ps && docker images", "docker ps ; ls", "docker ps > out.txt"):
            with self.assertRaises(shell.UnsupportedCommand, msg=cmd):
                shell.parse(cmd)

    def test_every_command_constant_parses_without_a_shell(self):
        """A new docker/commands.py constant that needs a pipe or && would silently break on Windows."""
        from src.docker import commands
        values = collections.defaultdict(lambda: "x")
        checked = 0
        with patch.object(shell.subprocess, "run", return_value=MagicMock(stdout="id1\n")):
            for name in dir(commands):
                value = getattr(commands, name)
                if name.startswith("DOCKER_") and isinstance(value, str):
                    shell.parse(value.format_map(values))
                    checked += 1
        self.assertGreater(checked, 50)


class TestShellRun(unittest.TestCase):

    def test_output_merges_streams_and_strips(self):
        out = shell.output(f'"{sys.executable}" -c "import sys; print(\'a\'); print(\'b\', file=sys.stderr)"')
        self.assertEqual(sorted(out.split()), ["a", "b"])

    def test_discarded_stderr(self):
        cmd = f'"{sys.executable}" -c "import sys; print(\'a\'); print(\'b\', file=sys.stderr)" 2>/dev/null'
        self.assertEqual(shell.output(cmd), "a")

    def test_stdin_input_is_delivered(self):
        cmd = f'"{sys.executable}" -c "import sys; print(sys.stdin.read().upper())"'
        self.assertEqual(shell.output(cmd, input_text="token"), "TOKEN")

    def test_missing_program_is_reported_as_text(self):
        self.assertIn("definitely-not-a-program", shell.output("definitely-not-a-program --x"))

    def test_unsupported_syntax_is_reported_as_text(self):
        self.assertIn("not supported", shell.output("docker ps | grep x"))

    def test_run_cmd_uses_the_parser_on_windows(self):
        from src.utils.utils import run_cmd
        with patch.object(plat, "IS_WIN", True), patch.object(plat, "IS_LINUX", False), \
                patch("src.utils.utils.shell.output", return_value="ok") as out:
            self.assertEqual(run_cmd("docker ps", sudo=True, sudo_password="pw"), "ok")
        self.assertEqual(out.call_args[0][0], "docker ps")    # no `sudo -S` prefix

    def test_windows_creation_flags_hide_the_console(self):
        with patch.object(plat, "IS_WIN", True):
            flags = plat.popen_flags(new_group=True)["creationflags"]
        self.assertTrue(flags & 0x08000000)       # CREATE_NO_WINDOW
        self.assertTrue(flags & 0x00000200)       # CREATE_NEW_PROCESS_GROUP
        with patch.object(plat, "IS_WIN", False):
            self.assertEqual(plat.popen_flags(new_group=True), {})     # POSIX uses start_new_session instead


# ===========================================================================
# sudo only exists on Linux
# ===========================================================================

class TestSudoPerPlatform(unittest.TestCase):

    def test_only_linux_uses_sudo(self):
        for name, expected in (("linux", True), ("mac", False), ("win", False)):
            patches = _as(name)
            for p in patches:
                p.start()
            try:
                self.assertEqual(plat.uses_sudo(), expected, name)
            finally:
                for p in patches:
                    p.stop()

    def test_docker_desktop_users_are_never_asked_for_a_password(self):
        from src.utils.utils import docker_needs_sudo
        for name in ("mac", "win"):
            patches = _as(name)
            for p in patches:
                p.start()
            try:
                with patch("src.utils.utils.subprocess.run") as run:
                    self.assertFalse(docker_needs_sudo(), name)
                    run.assert_not_called()
            finally:
                for p in patches:
                    p.stop()

    def test_run_cmd_does_not_prefix_sudo_on_macos(self):
        from src.utils.utils import run_cmd
        with patch.object(plat, "IS_LINUX", False), patch.object(plat, "IS_MAC", True), \
                patch("src.utils.utils.subprocess.check_output", return_value="ok\n") as out, \
                patch("src.utils.utils.subprocess.Popen") as popen:
            run_cmd("docker ps", sudo=True, sudo_password="pw")
        popen.assert_not_called()
        self.assertEqual(out.call_args[0][0], "docker ps")

    def test_keyring_is_linux_only(self):
        from src.config import config_manager as cm
        with patch.object(plat, "IS_LINUX", False), patch.object(cm.shutil, "which", return_value="/x/secret-tool"):
            self.assertFalse(cm.keyring_available())


# ===========================================================================
# Docker service: systemd, Docker Desktop, or nothing
# ===========================================================================

class TestServiceManager(unittest.TestCase):

    def test_linux_with_systemctl_uses_systemd(self):
        with patch.object(plat, "IS_LINUX", True), patch.object(plat.shutil, "which", return_value="/bin/systemctl"):
            self.assertEqual(plat.service_manager(), "systemd")

    def test_linux_without_systemctl_has_no_manager(self):
        with patch.object(plat, "IS_LINUX", True), patch.object(plat.shutil, "which", return_value=None):
            self.assertIsNone(plat.service_manager())

    def test_mac_and_windows_use_docker_desktop(self):
        for name in ("mac", "win"):
            patches = _as(name)
            for p in patches:
                p.start()
            try:
                self.assertEqual(plat.service_manager(), "desktop")
            finally:
                for p in patches:
                    p.stop()

    def test_status_without_systemd_asks_docker_itself(self):
        from src.utils.utils import docker_service_active
        with patch.object(plat, "service_manager", return_value="desktop"), \
                patch("src.utils.utils.subprocess.run", return_value=MagicMock(returncode=0, stdout="29.1\n")) as run:
            self.assertTrue(docker_service_active())
        self.assertEqual(run.call_args[0][0][:2], ["docker", "info"])
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_status_down_when_docker_info_fails(self):
        from src.utils.utils import docker_service_active
        with patch.object(plat, "service_manager", return_value="desktop"), \
                patch("src.utils.utils.subprocess.run", return_value=MagicMock(returncode=1, stdout="")):
            self.assertFalse(docker_service_active())

    def test_status_down_when_docker_is_missing(self):
        from src.utils.utils import docker_service_active
        with patch.object(plat, "service_manager", return_value="desktop"), \
                patch("src.utils.utils.subprocess.run", side_effect=FileNotFoundError):
            self.assertFalse(docker_service_active())


class TestDockerDesktopControl(unittest.TestCase):

    def _result(self, code, out=""):
        return MagicMock(returncode=code, stdout=out, stderr="")

    def test_uses_the_docker_desktop_cli_when_available(self):
        with patch.object(plat.subprocess, "run", return_value=self._result(0, "started")) as run:
            self.assertEqual(plat.docker_desktop_action("start"), "started")
        self.assertEqual(run.call_args[0][0], ["docker", "desktop", "start"])

    def test_macos_fallback_opens_and_quits_the_app(self):
        calls = []

        def fake_run(argv, **_kw):
            calls.append(argv)
            return self._result(1 if argv[:2] == ["docker", "desktop"] else 0)

        with patch.object(plat, "IS_MAC", True), patch.object(plat, "IS_WIN", False), \
                patch.object(plat.subprocess, "run", side_effect=fake_run):
            plat.docker_desktop_action("start")
            plat.docker_desktop_action("stop")
            plat.docker_desktop_action("restart")
        flat = [" ".join(c) for c in calls if c[:2] != ["docker", "desktop"]]
        self.assertEqual(flat, ["open -a Docker", 'osascript -e quit app "Docker"',
                                'osascript -e quit app "Docker"', "open -a Docker"])

    def test_windows_fallback_kills_and_launches_docker_desktop(self):
        calls = []

        def fake_run(argv, **_kw):
            calls.append(argv)
            return self._result(1 if argv[:2] == ["docker", "desktop"] else 0)

        with tempfile.TemporaryDirectory() as root:
            exe_dir = os.path.join(root, "Docker", "Docker")
            os.makedirs(exe_dir)
            exe = os.path.join(exe_dir, "Docker Desktop.exe")
            open(exe, "w").close()
            with patch.object(plat, "IS_MAC", False), patch.object(plat, "IS_WIN", True), \
                    patch.dict(os.environ, {"ProgramFiles": root}), \
                    patch.object(plat.subprocess, "run", side_effect=fake_run), \
                    patch.object(plat.subprocess, "Popen") as popen:
                plat.docker_desktop_action("stop")
                plat.docker_desktop_action("start")
        self.assertIn(["taskkill", "/F", "/IM", "Docker Desktop.exe"], calls)
        self.assertEqual(popen.call_args[0][0], [exe])

    def test_failure_is_reported(self):
        with patch.object(plat, "IS_MAC", True), patch.object(plat, "IS_WIN", False), \
                patch.object(plat.subprocess, "run", return_value=self._result(1, "boom")):
            self.assertEqual(plat.docker_desktop_action("start"), "boom")


class TestServiceButtonsPerPlatform(unittest.TestCase):

    def _run(self, manager, action="start", **patches):
        from src.docker import actions
        output = []
        with patch.object(actions.plat, "service_manager", return_value=manager), \
                patch.object(actions, "startThreadForTask", side_effect=lambda t: t()), \
                patch.object(actions, "update_docker_status"), \
                patch.object(actions, "docker_service_active", return_value=True), \
                patch.object(actions, "get_sudo_password", return_value="pw"), \
                patch("time.sleep"):
            with patch.object(actions, "run_cmd", return_value="sysd") as run_cmd, \
                    patch.object(actions.plat, "docker_desktop_action", return_value="desktop") as desktop:
                root = MagicMock()
                getattr(actions, f"{action}_docker_service")(root, MagicMock(), MagicMock(), output.append)
        return output, run_cmd, desktop

    def test_systemd_path_is_unchanged(self):
        output, run_cmd, desktop = self._run("systemd")
        run_cmd.assert_called_once_with("systemctl start docker.socket docker.service", sudo=True, sudo_password="pw")
        desktop.assert_not_called()
        self.assertIn("sysd", output[0])

    def test_desktop_path_never_touches_systemctl(self):
        for action in ("start", "stop", "restart"):
            output, run_cmd, desktop = self._run("desktop", action)
            run_cmd.assert_not_called()
            desktop.assert_called_with(action)
            self.assertIn("desktop", output[0])

    def test_no_manager_explains_instead_of_failing(self):
        output, run_cmd, desktop = self._run(None, "stop")
        run_cmd.assert_not_called()
        desktop.assert_not_called()
        self.assertIn("no systemd", output[0])


# ===========================================================================
# Notifications
# ===========================================================================

class TestNotificationCommands(unittest.TestCase):

    def _command(self, name, which):
        from src.utils.utils import notification_command
        patches = _as(name) + [patch("src.utils.utils.shutil.which", side_effect=which)]
        for p in patches:
            p.start()
        try:
            return notification_command('Build "x"', 'it\'s done\\')
        finally:
            for p in patches:
                p.stop()

    def test_linux_notify_send(self):
        argv, env = self._command("linux", lambda n: "/usr/bin/" + n if n == "notify-send" else None)
        self.assertEqual(argv, ["notify-send", "--app-name=Docker Control Panel", 'Build "x"', "it's done\\"])

    def test_macos_osascript_escapes_quotes(self):
        argv, _ = self._command("mac", lambda n: "/usr/bin/osascript" if n == "osascript" else None)
        self.assertEqual(argv[:2], ["osascript", "-e"])
        self.assertIn('with title "Build \\"x\\""', argv[2])
        self.assertIn('"it\'s done\\\\"', argv[2])

    def test_windows_powershell_gets_text_through_the_environment(self):
        argv, env = self._command("win", lambda n: "C:/ps/powershell.exe" if n == "powershell" else None)
        self.assertEqual(env, {"DCP_TITLE": 'Build "x"', "DCP_MESSAGE": "it's done\\"})
        self.assertNotIn("done", " ".join(argv))       # never interpolated into the script

    def test_none_when_the_os_has_no_tool(self):
        for name in ("linux", "mac", "win"):
            self.assertIsNone(self._command(name, lambda n: None), name)

    def test_hint_names_the_missing_tool(self):
        from src.utils.utils import notification_hint
        patches = _as("mac") + [patch("src.utils.utils.shutil.which", return_value=None)]
        for p in patches:
            p.start()
        try:
            self.assertIn("osascript", notification_hint())
        finally:
            for p in patches:
                p.stop()


# ===========================================================================
# Terminals
# ===========================================================================

class TestTerminals(unittest.TestCase):

    def _with(self, name, fn, which=lambda n: None, **extra):
        patches = _as(name) + [patch.object(terminals.shutil, "which", side_effect=which)]
        for p in patches:
            p.start()
        try:
            return fn()
        finally:
            for p in patches:
                p.stop()

    def test_macos_always_has_terminal_app(self):
        self.assertEqual(self._with("mac", terminals.installed_terminals)[:1], ["Terminal"])

    def test_windows_always_has_cmd_and_wt_when_installed(self):
        self.assertEqual(self._with("win", terminals.installed_terminals), ["cmd"])
        self.assertEqual(self._with("win", terminals.installed_terminals, which=lambda n: "C:/wt.exe"), ["wt", "cmd"])

    def test_linux_lists_only_installed_emulators(self):
        found = self._with("linux", terminals.installed_terminals, which=lambda n: "/x" if n in ("xterm", "tilix") else None)
        self.assertEqual(found, ["tilix", "xterm"])

    def test_commands_per_platform(self):
        mac = self._with("mac", lambda: terminals._command("Terminal", "T", "/tmp/s.command"))
        self.assertEqual(mac[0], ["open", "-a", "Terminal", "/tmp/s.command"])
        wt = self._with("win", lambda: terminals._command("wt", "T", r"C:\s.cmd"))
        self.assertEqual(wt[0], ["wt", "new-tab", "--title", "T", "cmd", "/c", r"C:\s.cmd"])
        console = self._with("win", lambda: terminals._command("cmd", "T", r"C:\s.cmd"))
        self.assertEqual(console[0], ["cmd", "/c", r"C:\s.cmd"])
        self.assertEqual(console[1]["creationflags"], 0x10)      # CREATE_NEW_CONSOLE: its own window
        linux = self._with("linux", lambda: terminals._command("gnome-terminal", "T", "/tmp/s.sh"))
        self.assertEqual(linux[0], ["gnome-terminal", "--title", "T", "--", "bash", "/tmp/s.sh"])

    def test_scripts_have_the_right_shape_for_each_shell(self):
        def make(name):
            path = self._with(name, lambda: terminals.write_script(["echo hi"]))
            try:
                with open(path, "rb") as handle:
                    return path, handle.read()
            finally:
                os.unlink(path)
        path, body = make("linux")
        self.assertTrue(path.endswith(".sh") and body.startswith(b"#!/bin/bash\n"))
        path, body = make("mac")
        self.assertTrue(path.endswith(".command") and body.startswith(b"#!/bin/bash\n"))
        path, body = make("win")
        self.assertTrue(path.endswith(".cmd") and body == b"echo hi\r\n")

    def test_launch_tries_the_preferred_one_first_and_falls_back(self):
        attempts = []

        def popen(argv, **_kw):
            attempts.append(argv[0])
            if argv[0] == "xterm":
                raise FileNotFoundError
            return MagicMock(wait=MagicMock(side_effect=subprocess.TimeoutExpired("x", 1)))

        with patch.object(terminals.subprocess, "Popen", side_effect=popen):
            ok, error = self._with("linux", lambda: terminals.launch("/tmp/s.sh", "T", preferred="xterm"),
                                   which=lambda n: "/x" if n in ("xterm", "tilix") else None)
        self.assertTrue(ok)
        self.assertEqual(attempts, ["xterm", "tilix"])

    def test_launch_reports_why_nothing_opened(self):
        with patch.object(terminals.subprocess, "Popen", side_effect=FileNotFoundError):
            ok, error = self._with("linux", lambda: terminals.launch("/tmp/s.sh", "T"),
                                   which=lambda n: "/x" if n == "xterm" else None)
        self.assertFalse(ok)
        self.assertIn("xterm", error)

    def test_macos_launch_succeeds_once_open_returns(self):
        with patch.object(terminals.subprocess, "Popen") as popen:
            ok, _ = self._with("mac", lambda: terminals.launch("/tmp/s.command", "T"))
        self.assertTrue(ok)
        self.assertEqual(popen.call_args[0][0][:3], ["open", "-a", "Terminal"])


# ===========================================================================
# Environment / UI details
# ===========================================================================

class TestEnvironment(unittest.TestCase):

    def test_xim_opt_out_only_on_linux(self):
        for name, expected in (("linux", "@im=none"), ("mac", None), ("win", None)):
            patches = _as(name) + [patch.dict(os.environ, {}, clear=False)]
            for p in patches:
                p.start()
            os.environ.pop("XMODIFIERS", None)
            try:
                with patch.object(plat, "_extend_path"):
                    plat.prepare_environment()
                self.assertEqual(os.environ.get("XMODIFIERS"), expected, name)
            finally:
                for p in reversed(patches):
                    p.stop()

    def test_mac_path_gains_docker_locations_that_exist(self):
        with tempfile.TemporaryDirectory() as bin_dir:
            with patch.object(plat, "IS_MAC", True), patch.object(plat, "IS_WIN", False), \
                    patch.object(plat, "_MAC_PATHS", [bin_dir, "/no/such/dir"]), \
                    patch.dict(os.environ, {"PATH": "/usr/bin"}):
                plat._extend_path()
                self.assertEqual(os.environ["PATH"], os.pathsep.join(["/usr/bin", bin_dir]))
                plat._extend_path()                       # idempotent
                self.assertEqual(os.environ["PATH"].count(bin_dir), 1)

    def test_venv_layout_differs_on_windows(self):
        with patch.object(plat, "IS_WIN", True):
            self.assertEqual(plat.venv_site_packages_globs(), [os.path.join(".venv", "Lib", "site-packages")])
        with patch.object(plat, "IS_WIN", False):
            self.assertIn("python*", plat.venv_site_packages_globs()[0])

    def test_wheel_is_bound_to_buttons_4_5_only_on_linux(self):
        from src.ui.scroll_frame import ScrollFrame
        with patch.object(plat, "IS_LINUX", True):
            self.assertIn("<Button-4>", ScrollFrame._wheel_sequences())
        with patch.object(plat, "IS_LINUX", False):
            self.assertEqual(ScrollFrame._wheel_sequences(), ("<MouseWheel>",))

    def test_docker_config_is_read_directly_on_windows(self):
        from src.images import dialogs
        with tempfile.TemporaryDirectory() as home:
            with open(os.path.join(home, "config.json"), "w", encoding="utf-8") as handle:
                handle.write('{"auths": {"ghcr.io": {}}}')
            with patch.object(dialogs.plat, "IS_WIN", True), patch.dict(os.environ, {"DOCKER_CONFIG": home}), \
                    patch.object(dialogs, "run_cmd") as run:
                text = dialogs.read_docker_config()
            run.assert_not_called()
        self.assertEqual(dialogs.parse_registries(text), ["ghcr.io"])

    def test_install_docker_script_per_platform(self):
        from src.ui import ui_components
        patches = _as("mac") + [patch.object(ui_components.shutil, "which", return_value=None)]
        for p in patches:
            p.start()
        try:
            self.assertIsNone(ui_components._docker_install_script())      # no brew: manual download
        finally:
            for p in patches:
                p.stop()
        patches = _as("win") + [patch.object(ui_components.shutil, "which", return_value="winget.exe")]
        for p in patches:
            p.start()
        try:
            self.assertTrue(any("winget install -e --id Docker.DockerDesktop" in l
                                for l in ui_components._docker_install_script()))
        finally:
            for p in patches:
                p.stop()
        with patch.object(plat, "IS_LINUX", True), patch.object(plat, "IS_MAC", False), patch.object(plat, "IS_WIN", False):
            self.assertIn("apt-get", " ".join(ui_components._docker_install_script()))


if __name__ == "__main__":
    unittest.main()
