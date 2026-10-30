"""
Tests for the distro-independence layer: which init system controls Docker, how the service
buttons and status behave on each, terminal emulators and the install hints. Everything is mocked,
so every branch runs on any host.
"""

import os
import stat
import subprocess
import types
import unittest
from unittest.mock import patch, MagicMock

from src.utils import platform_utils as plat, terminals


def _host(systemd=False, tools=()):
    """Pretend the machine runs systemd (or not) and has exactly these programs / directories."""
    fake_os = types.SimpleNamespace(
        environ=os.environ,
        path=types.SimpleNamespace(isdir=lambda p: (systemd and p == "/run/systemd/system") or p in tools))
    return [
        patch.object(plat, "os", fake_os),       # only the module's own view of the filesystem
        patch.object(plat.shutil, "which", side_effect=lambda n: f"/usr/bin/{n}" if n in tools else None),
    ]


class _Host(unittest.TestCase):
    def host(self, **kw):
        for p in _host(**kw):
            p.start()
            self.addCleanup(p.stop)


class TestServiceManager(_Host):

    def test_systemd_when_it_is_pid_1(self):
        self.host(systemd=True, tools=("systemctl", "service"))
        self.assertEqual(plat.service_manager(), "systemd")

    def test_systemctl_alone_is_not_systemd(self):
        """WSL1 / containers ship systemctl without running systemd."""
        self.host(systemd=False, tools=("systemctl",))
        self.assertIsNone(plat.service_manager())

    def test_openrc_alpine(self):
        self.host(tools=("rc-service", "rc-update"))
        self.assertEqual(plat.service_manager(), "openrc")

    def test_runit_void(self):
        self.host(tools=("sv", "/var/service"))
        self.assertEqual(plat.service_manager(), "runit")

    def test_sysv_service_command(self):
        self.host(tools=("service",))
        self.assertEqual(plat.service_manager(), "sysv")

    def test_nothing_known(self):
        self.host()
        self.assertIsNone(plat.service_manager())

    def test_commands_per_init_system(self):
        expected = {
            "systemd": {"start": "systemctl start docker.socket docker.service",
                        "restart": "systemctl restart docker.socket docker.service"},
            "openrc": {"stop": "rc-service docker stop"},
            "sysv": {"start": "service docker start"},
            "runit": {"start": "sv up docker", "stop": "sv down docker", "restart": "sv restart docker"},
        }
        for manager, commands in expected.items():
            with patch.object(plat, "service_manager", return_value=manager):
                for action, command in commands.items():
                    self.assertEqual(plat.service_command(action), command, (manager, action))

    def test_no_command_without_an_init_system(self):
        with patch.object(plat, "service_manager", return_value=None):
            self.assertIsNone(plat.service_command("start"))
        self.assertIn("no init system", plat.no_service_manager_text("start"))

    def test_package_manager_detection(self):
        self.host(tools=("dnf", "pacman"))
        self.assertEqual(plat.package_manager(), "dnf")

    def test_package_manager_alpine(self):
        self.host(tools=("apk",))
        self.assertEqual(plat.package_manager(), "apk")


class TestServiceButtons(unittest.TestCase):

    def _press(self, manager, action="start"):
        from src.docker import actions
        output = []
        with patch.object(actions.plat, "service_manager", return_value=manager), \
                patch.object(actions, "startThreadForTask", side_effect=lambda t: t()), \
                patch.object(actions, "update_docker_status"), \
                patch.object(actions, "get_sudo_password", return_value="pw"), \
                patch.object(actions, "run_cmd", return_value="done") as run, \
                patch("time.sleep"):
            getattr(actions, f"{action}_docker_service")(MagicMock(), MagicMock(), MagicMock(), output.append)
        return output, run

    def test_each_init_system_gets_its_own_command(self):
        for manager, command in (("systemd", "systemctl start docker.socket docker.service"),
                                 ("openrc", "rc-service docker start"), ("sysv", "service docker start"),
                                 ("runit", "sv up docker")):
            output, run = self._press(manager)
            run.assert_called_once_with(command, sudo=True, sudo_password="pw")
            self.assertIn("done", output[0])

    def test_without_an_init_system_the_button_explains(self):
        output, run = self._press(None, "stop")
        run.assert_not_called()
        self.assertIn("no init system", output[0])


class TestStatus(unittest.TestCase):

    def _status(self, manager, is_active, info):
        from src.utils import utils
        with patch.object(utils.plat, "service_manager", return_value=manager), \
                patch.object(utils.subprocess, "run") as run:
            def fake(args, **_kw):
                if isinstance(args, str):               # systemctl is-active docker
                    return MagicMock(stdout=is_active)
                return MagicMock(returncode=0 if info else 1, stdout="27.0\n" if info else "")
            run.side_effect = fake
            return utils.docker_service_active()

    def test_systemd_active(self):
        self.assertTrue(self._status("systemd", "active\n", info=False))

    def test_systemd_inactive_but_the_cli_answers(self):
        """Snap / rootless Docker, or a remote docker context: the unit is not called 'docker'."""
        self.assertTrue(self._status("systemd", "inactive\n", info=True))

    def test_systemd_inactive_and_no_answer_is_stopped(self):
        self.assertFalse(self._status("systemd", "inactive\n", info=False))

    def test_without_systemd_only_the_cli_decides(self):
        self.assertTrue(self._status("openrc", "", info=True))
        self.assertFalse(self._status(None, "", info=False))

    def test_missing_cli_is_stopped_not_a_crash(self):
        from src.utils import utils
        with patch.object(utils.plat, "service_manager", return_value=None), \
                patch.object(utils.subprocess, "run", side_effect=FileNotFoundError):
            self.assertFalse(utils.docker_service_active())


class TestTerminals(_Host):

    def test_only_installed_emulators_are_listed_in_preference_order(self):
        self.host(tools=("xterm", "kitty", "ptyxis"))
        self.assertEqual(terminals.installed_terminals(), ["ptyxis", "kitty", "xterm"])

    def test_every_emulator_builds_a_command_that_ends_in_the_script(self):
        for name, build in terminals._TERMINALS.items():
            argv = build("My title", "/tmp/s.sh")
            self.assertEqual(argv[0], name)
            self.assertIn("/tmp/s.sh", argv)

    def test_launch_prefers_the_settings_choice_and_falls_back(self):
        self.host(tools=("xterm", "tilix"))
        tried = []

        def popen(argv, **_kw):
            tried.append(argv[0])
            if argv[0] == "xterm":
                raise FileNotFoundError
            return MagicMock(wait=MagicMock(side_effect=subprocess.TimeoutExpired("x", 1)))

        with patch.object(terminals.subprocess, "Popen", side_effect=popen):
            ok, _ = terminals.launch("/tmp/s.sh", "T", preferred="xterm")
        self.assertTrue(ok)
        self.assertEqual(tried, ["xterm", "tilix"])

    def test_an_emulator_that_exits_at_once_is_skipped(self):
        self.host(tools=("xterm", "konsole"))
        dead = MagicMock(wait=MagicMock(return_value=1), stderr=MagicMock(read=lambda: b"no display"))
        alive = MagicMock(wait=MagicMock(side_effect=subprocess.TimeoutExpired("x", 1)))
        with patch.object(terminals.subprocess, "Popen", side_effect=[dead, alive]) as popen:
            ok, _ = terminals.launch("/tmp/s.sh", "T")        # konsole dies at once, xterm takes over
        self.assertTrue(ok)
        self.assertEqual([c[0][0][0] for c in popen.call_args_list], ["konsole", "xterm"])

    def test_reports_the_last_error_when_nothing_opens(self):
        self.host(tools=("xterm",))
        dead = MagicMock(wait=MagicMock(return_value=2), stderr=MagicMock(read=lambda: b"cannot open display"))
        with patch.object(terminals.subprocess, "Popen", return_value=dead):
            ok, error = terminals.launch("/tmp/s.sh", "T")
        self.assertFalse(ok)
        self.assertIn("cannot open display", error)

    def test_install_hint_uses_the_distros_package_manager(self):
        for tool, expected in (("apt-get", "sudo apt install xterm"), ("dnf", "sudo dnf install xterm"),
                               ("pacman", "sudo pacman -S xterm"), ("apk", "sudo apk add xterm")):
            with patch.object(terminals.plat, "package_manager", return_value=tool):
                self.assertEqual(terminals.install_hint(), expected)
        with patch.object(terminals.plat, "package_manager", return_value=None):
            self.assertIn("terminal emulator", terminals.install_hint())

    def test_scripts_use_env_bash_and_are_executable(self):
        path = terminals.write_script(["echo hi"])
        try:
            with open(path) as handle:
                self.assertEqual(handle.read(), "#!/usr/bin/env bash\necho hi\n")
            self.assertTrue(os.stat(path).st_mode & stat.S_IXUSR)
        finally:
            os.unlink(path)


class TestInstallDockerPrompt(unittest.TestCase):

    def test_script_covers_every_package_manager_and_init_system(self):
        from src.ui.ui_components import _INSTALL_DOCKER
        text = "\n".join(_INSTALL_DOCKER)
        for needed in ("apt-get", "dnf", "yum", "pacman", "zypper", "apk add docker", "xbps-install",
                       "systemctl enable --now docker", "rc-update add docker", "/etc/sv/docker"):
            self.assertIn(needed, text)

    def test_declining_launches_nothing(self):
        from src.ui import ui_components
        with patch.object(ui_components.messagebox, "askyesno", return_value=False), \
                patch.object(ui_components.terminals, "launch") as launch:
            ui_components.prompt_docker_installation()
        launch.assert_not_called()

    def test_failure_to_open_a_terminal_points_to_the_docs(self):
        from src.ui import ui_components
        with patch.object(ui_components.messagebox, "askyesno", return_value=True), \
                patch.object(ui_components.terminals, "write_script", return_value="/tmp/x.sh"), \
                patch.object(ui_components.terminals, "launch", return_value=(False, "none")), \
                patch.object(ui_components.messagebox, "showwarning") as warn:
            ui_components.prompt_docker_installation()
        self.assertIn("docs.docker.com", warn.call_args[0][1])


class TestOldPythons(unittest.TestCase):

    def test_push_target_works_without_removeprefix(self):
        """str.removeprefix is Python 3.9+; Ubuntu 20.04 still ships 3.8."""
        from src.images.dialogs import _push_target
        self.assertEqual(_push_target("library/nginx:1", "me"), "me/nginx:1")
        self.assertEqual(_push_target("nginx", "me"), "me/nginx")
        self.assertEqual(_push_target("other/app", "me"), "me/other/app")

    def test_no_python_39_only_string_methods_in_the_sources(self):
        import glob
        import re
        pattern = re.compile(r"\.(removeprefix|removesuffix)\(")
        offenders = []
        for path in glob.glob("src/**/*.py", recursive=True) + ["docker_gui_modular.py"]:
            with open(path, encoding="utf-8") as handle:
                if pattern.search(handle.read()):
                    offenders.append(path)
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
