"""
Tests for the Docker home page: the live "How it works" card, the tooltips on its buttons, the
creator details, and the shipped images.
"""

import glob
import os
import struct
import sys
import time
import tkinter as tk
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock

# Stub ttkbootstrap before any app module is imported (as test_buttons.py does): a real Style singleton
# would stay bound to the first, destroyed test window
sys.modules.setdefault('ttkbootstrap', MagicMock())

from src.system import overview
from src.ui import workflow_view
from src.ui.workflow_view import build_nodes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UP = {"engine": "docker", "cli_path": "/usr/bin/docker", "access": "direct", "init": "systemd",
      "client_version": "29.1.3", "server_version": "29.1.3", "context": "default",
      "host": "unix:///var/run/docker.sock", "containers": "32", "running": "16", "images": "279",
      "os": "Ubuntu 26.04 LTS"}


class TestBuildNodes(unittest.TestCase):

    def test_running_docker_shows_what_is_in_use(self):
        titles = [t for t, _ in build_nodes(UP)]
        self.assertEqual(titles, ["This app", "docker CLI", "Docker Engine", "Your Docker"])
        flat = " | ".join(" ".join(lines) for _, lines in build_nodes(UP))
        for text in ("/usr/bin/docker", "version 29.1.3", "directly (no sudo needed)", "dockerd 29.1.3",
                     "unix:///var/run/docker.sock", "managed by systemd", "16 of 32 containers running",
                     "279 images", "Ubuntu 26.04 LTS"):
            self.assertIn(text, flat)

    def test_sudo_access_is_stated(self):
        lines = build_nodes(dict(UP, access="sudo"))[1][1]
        self.assertIn("through sudo", " ".join(lines))

    def test_unreachable_daemon(self):
        info = dict(UP, server_version=None, containers=None, running=None, images=None, os=None, host=None)
        nodes = build_nodes(info)
        self.assertIn("not reachable", nodes[2][1])
        self.assertIn("is Docker running?", nodes[2][1])
        self.assertIn("appear here", " ".join(nodes[3][1]))

    def test_missing_cli_and_no_init_system(self):
        info = {"engine": "docker", "cli_path": None, "init": None}
        nodes = build_nodes(info)
        self.assertIn("docker not found", nodes[1][1])
        self.assertIn("no init system", " ".join(nodes[2][1]))

    def test_podman_has_no_daemon(self):
        nodes = build_nodes({"engine": "podman", "cli_path": "/usr/bin/podman", "access": "direct"})
        self.assertEqual([t for t, _ in nodes][1:], ["podman CLI", "Podman", "Your Podman"])
        self.assertIn("no daemon", " ".join(nodes[2][1]))


class TestOverview(unittest.TestCase):

    def _gather(self, outputs, engine="docker", which="/usr/bin/docker", password=None):
        def fake(command, **_kw):
            for needle, text in outputs.items():
                if needle in command:
                    return text
            return ""
        with patch.object(overview, "engine", return_value=engine), \
                patch.object(overview.shutil, "which", return_value=which), \
                patch.object(overview, "get_sudo_password", return_value=password), \
                patch.object(overview.plat, "service_manager", return_value="openrc"), \
                patch.object(overview, "run_cmd", side_effect=fake):
            return overview.gather_overview()

    def test_collects_every_field(self):
        info = self._gather({"Client.Version": "29.1.3\n", "context show": "default\n",
                             "context inspect": "unix:///run/docker.sock\n",
                             "ServerVersion": "29.1.3\t10\t4\t55\tAlpine Linux\n"}, password="pw")
        self.assertEqual((info["client_version"], info["server_version"], info["containers"], info["running"],
                          info["images"], info["os"]), ("29.1.3", "29.1.3", "10", "4", "55", "Alpine Linux"))
        self.assertEqual((info["context"], info["host"], info["init"], info["access"]),
                         ("default", "unix:///run/docker.sock", "openrc", "sudo"))

    def test_error_messages_become_unknown_not_values(self):
        info = self._gather({"Client.Version": "29.1.3", "context": "Error: no such context",
                             "ServerVersion": "permission denied while trying to connect to the Docker daemon socket"})
        self.assertEqual(info["client_version"], "29.1.3")
        self.assertIsNone(info["context"])
        self.assertIsNone(info["server_version"])
        self.assertIsNone(info["containers"])

    def test_missing_cli_stops_early(self):
        with patch.object(overview, "run_cmd") as run:
            info = self._gather({}, which=None)
        self.assertIsNone(info["cli_path"])
        run.assert_not_called()

    def test_podman_skips_the_daemon_queries(self):
        seen = []
        with patch.object(overview, "engine", return_value="podman"), \
                patch.object(overview.shutil, "which", return_value="/usr/bin/podman"), \
                patch.object(overview, "get_sudo_password", return_value=None), \
                patch.object(overview.plat, "service_manager", return_value="systemd"), \
                patch.object(overview, "run_cmd", side_effect=lambda c, **_k: seen.append(c) or "5.0.0"):
            info = overview.gather_overview()
        self.assertEqual(len(seen), 1)               # only the client version
        self.assertEqual(info["client_version"], "5.0.0")
        self.assertIsNone(info["server_version"])


class _Tk(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        sync = patch.object(workflow_view, "startThreadForTask", side_effect=lambda task: task())
        sync.start()
        self.addCleanup(sync.stop)

    def settle(self, seconds=0.2):
        """Let Tk run its deferred work (the card redraws 30 ms after a change)."""
        end = time.time() + seconds
        while time.time() < end:
            self.root.update()
            time.sleep(0.01)

    def texts(self, widget):
        return [widget.itemcget(i, "text") for i in widget.find_all() if widget.type(i) == "text"]


class TestWorkflowDiagram(_Tk):

    def _diagram(self, fetch, width=900):
        diagram = workflow_view.WorkflowDiagram(self.root, fetch)
        diagram.pack(fill=tk.X)
        self.root.geometry(f"{width}x500")
        self.settle()
        return diagram

    def test_draws_the_live_values(self):
        diagram = self._diagram(lambda: UP)
        diagram.refresh()
        self.settle()
        texts = self.texts(diagram.canvas)
        for expected in ("This app", "docker CLI", "Docker Engine", "Your Docker", "dockerd 29.1.3",
                         "runs", "API", "owns"):
            self.assertIn(expected, texts)
        self.assertIn("Live", diagram._caption.cget("text"))

    def test_wide_window_lays_nodes_out_in_a_row_and_narrow_in_a_column(self):
        diagram = self._diagram(lambda: UP, width=1000)
        diagram.refresh()
        self.settle()

        def title_positions():
            canvas = diagram.canvas
            by_text = {canvas.itemcget(i, "text"): canvas.coords(i) for i in canvas.find_all()
                       if canvas.type(i) == "text"}
            return [by_text[t] for t in ("This app", "docker CLI", "Docker Engine", "Your Docker")]

        xs = [p[0] for p in title_positions()]
        ys = [p[1] for p in title_positions()]
        self.assertEqual(xs, sorted(xs))
        self.assertEqual(len(set(ys)), 1)                       # one row
        self.root.geometry("520x700")
        self.settle()
        ys = [p[1] for p in title_positions()]
        self.assertEqual(ys, sorted(ys))
        self.assertEqual(len(set(ys)), 4)                       # one column

    def test_failed_fetch_keeps_the_last_good_result(self):
        results = [UP, RuntimeError("boom")]

        def fetch():
            value = results.pop(0)
            if isinstance(value, Exception):
                raise value
            return value
        diagram = self._diagram(fetch)
        diagram.refresh()
        diagram.refresh()
        self.settle()
        self.assertIn("dockerd 29.1.3", self.texts(diagram.canvas))

    def test_first_failure_says_so(self):
        diagram = self._diagram(MagicMock(side_effect=RuntimeError("boom")))
        diagram.refresh()
        self.settle()
        self.assertIn("Could not read", diagram._caption.cget("text"))

    def test_a_refresh_during_a_refresh_runs_once_more(self):
        calls = []
        diagram = self._diagram(lambda: calls.append(1) or UP)
        with patch.object(workflow_view, "startThreadForTask") as start:      # worker not finished yet
            diagram.refresh()
            diagram.refresh()
            diagram.refresh()
            self.assertEqual(start.call_count, 1)
        self.assertTrue(diagram._again)

    def test_long_values_are_shortened_not_overflowing(self):
        info = dict(UP, host="unix:///a/very/long/path/to/some/remote/docker/engine/socket/that/never/ends.sock")
        diagram = self._diagram(lambda: info, width=760)
        diagram.refresh()
        self.settle()
        shown = [t for t in self.texts(diagram.canvas) if t.startswith("unix:")]
        self.assertTrue(shown and shown[0].endswith("…"))


class TestLandingTooltips(_Tk):

    def _landing(self, **kw):
        from src.ui import landing_page
        self.root.geometry("1000x700")
        landing = landing_page.LandingPage(
            self.root, tk.StringVar(master=self.root), [("Start", lambda: None), ("Stop", lambda: None),
                                                        ("Restart", lambda: None), ("Clean All", lambda: None)],
            lambda _c: None, ["Containers", "Images"], fetch_overview=lambda: UP, **kw)
        landing.pack(fill=tk.BOTH, expand=True)
        self.settle()
        return landing

    def test_every_service_button_has_a_tooltip(self):
        from src.config.config_tooltips import CATEGORY_TOOLTIPS, SIDEBAR_TOOLTIPS
        from src.ui import landing_page
        with patch.object(landing_page, "Tooltip") as tooltip:
            self._landing(button_tips=CATEGORY_TOOLTIPS["Docker"], category_tips=SIDEBAR_TOOLTIPS)
        tips = {}
        for call in tooltip.call_args_list:
            widget, text = call[0][0], call[0][1]
            if isinstance(widget, tk.Widget) and widget.winfo_class() == "TButton":
                tips.setdefault(widget.cget("text"), []).append(text)
        for label in ("Start", "Stop", "Restart", "Clean All"):
            self.assertEqual(tips[label], [CATEGORY_TOOLTIPS["Docker"][label]])
        self.assertEqual(sorted(tips["Open  →"]),                                  # the category cards too
                         sorted([SIDEBAR_TOOLTIPS["Containers"], SIDEBAR_TOOLTIPS["Images"]]))

    def test_no_tooltip_text_is_empty(self):
        from src.config.config_tooltips import CATEGORY_TOOLTIPS
        for label in ("Start", "Stop", "Restart", "Clean All"):
            self.assertTrue(CATEGORY_TOOLTIPS["Docker"][label].strip())

    def test_the_card_is_on_the_page_and_refreshes_when_the_status_changes(self):
        landing = self._landing()
        self.assertIsInstance(landing.workflow, workflow_view.WorkflowDiagram)
        landing.workflow.refresh()
        self.settle()
        self.assertIn("dockerd 29.1.3", self.texts(landing.workflow.canvas))
        with patch.object(landing.workflow, "refresh") as refresh:
            landing._refresh_if_visible()
        refresh.assert_called_once()


class TestCreatorDetails(unittest.TestCase):

    def test_role_and_email(self):
        from src.help import help_creator as hc
        self.assertEqual(hc.CREATOR_NAME, "Majid Ali")
        self.assertEqual(hc.CREATOR_ROLE, "Full Stack Developer")
        self.assertEqual(hc.CREATOR_EMAIL, "majidaliqau@gmail.com")
        self.assertEqual(hc.CREATOR_EMAIL_URL, "mailto:majidaliqau@gmail.com")

    def test_email_card_opens_mail_and_copies_the_plain_address(self):
        from src.help import creator_view
        email = [link for link in creator_view._LINKS if link[1] == "Email"]
        self.assertEqual(len(email), 1)
        _icon, _label, shown, url, copy_text = email[0]
        self.assertEqual((shown, url, copy_text),
                         ("majidaliqau@gmail.com", "mailto:majidaliqau@gmail.com", "majidaliqau@gmail.com"))

    def test_old_role_wording_is_gone_everywhere(self):
        files = (glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True)
                 + glob.glob(os.path.join(ROOT, "*.md")) + glob.glob(os.path.join(ROOT, ".github", "*.md")))
        for path in files:
            if ".venv" in path or path.endswith("test_home_page.py"):
                continue
            with open(path, encoding="utf-8") as handle:
                self.assertNotIn("Full Stack Web Developer", handle.read(), path)


class TestRequirements(unittest.TestCase):

    def test_ttkbootstrap_is_pinned_below_2(self):
        """2.x breaks the rounded styling (src/ui/rounded.py): a fresh install must not pick it up."""
        with open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8") as handle:
            lines = [line.strip() for line in handle if line.strip() and not line.startswith("#")]
        line = next(line for line in lines if line.lower().startswith("ttkbootstrap"))
        self.assertIn("<2", line)


class TestImages(unittest.TestCase):

    def test_icon_png_is_a_256px_png(self):
        with open(os.path.join(ROOT, "assets", "docker-icon.png"), "rb") as handle:
            head = handle.read(24)
        self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", head[16:24]), (256, 256))

    def test_svgs_are_well_formed_and_scalable(self):
        for name in ("docker-icon.svg", "workflow.svg"):
            tree = ET.parse(os.path.join(ROOT, "assets", name))
            self.assertTrue(tree.getroot().tag.endswith("svg"), name)
            self.assertIn("viewBox", tree.getroot().attrib, name)

    def test_workflow_diagram_names_every_stage(self):
        with open(os.path.join(ROOT, "assets", "workflow.svg"), encoding="utf-8") as handle:
            text = handle.read()
        for stage in ("The app", "docker CLI", "Docker Engine", "Your Docker", "systemd", "OpenRC", "runit", "SysV"):
            self.assertIn(stage, text)

    def test_the_icon_svg_is_self_contained(self):
        """No fonts or embedded images, so it renders the same in every menu, theme and renderer."""
        with open(os.path.join(ROOT, "assets", "docker-icon.svg"), encoding="utf-8") as handle:
            svg = handle.read()
        for forbidden in ("<text", "<image", "font-family", "href="):
            self.assertNotIn(forbidden, svg)
        self.assertIn('viewBox="0 0 512 512"', svg)

    def test_installer_puts_the_icon_in_the_icon_theme_and_the_menu_entry_uses_it(self):
        with open(os.path.join(ROOT, "install.sh"), encoding="utf-8") as handle:
            script = handle.read()
        for expected in ('ICON_ROOT="$HOME/.local/share/icons/hicolor"', "scalable/apps", "docker-icon.svg",
                         "256x256/apps", "docker-icon.png", 'Icon=$ICON_DEST', 'ICON_DEST="$ICON_NAME"'):
            self.assertIn(expected, script)
        with open(os.path.join(ROOT, "uninstall.sh"), encoding="utf-8") as handle:
            self.assertIn("hicolor/scalable/apps/docker-control-panel.svg", handle.read())

    def test_window_icon_is_loadable_by_tk(self):
        root = tk.Tk()
        try:
            image = tk.PhotoImage(file=os.path.join(ROOT, "assets", "docker-icon.png"))
            root.iconphoto(True, image)
            self.assertEqual(image.width(), 256)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
