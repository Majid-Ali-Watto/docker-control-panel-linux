"""
Tests for the Privacy Policy and Terms of Use: the shared source, the markdown files, first-run
acceptance, the reader dialogs and the links on the Docker home page.
"""

import os
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch, MagicMock

# Stub ttkbootstrap before any app module is imported (as test_buttons.py does)
sys.modules.setdefault('ttkbootstrap', MagicMock())

from src.config import config_manager as cm
from src.help import legal
from src.ui import legal_view

ROOT = Path(__file__).resolve().parent.parent
UP = {"engine": "docker", "cli_path": "/usr/bin/docker", "access": "direct", "init": "systemd"}


class _ConfigDir(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        patches = [patch.object(cm, "CONFIG_DIR", self.dir), patch.object(cm, "CONFIG_FILE", self.dir / "config.json"),
                   patch.dict(os.environ, {}, clear=False)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        os.environ.pop(legal_view.ACCEPT_ENV, None)
        self.addCleanup(self._tmp.cleanup)


class TestLegalText(unittest.TestCase):

    def test_markdown_files_match_the_source(self):
        """PRIVACY.md / TERMS.md are generated: run `python3 -m src.help.legal` after editing the text."""
        for kind, doc in legal.DOCUMENTS.items():
            self.assertEqual((ROOT / doc["file"]).read_text(encoding="utf-8"), legal.as_markdown(kind), doc["file"])

    def test_both_documents_are_complete(self):
        self.assertEqual(set(legal.DOCUMENTS), {"privacy", "terms"})
        for doc in legal.DOCUMENTS.values():
            self.assertTrue(doc["title"] and doc["intro"] and doc["sections"])
            for heading, paragraphs in doc["sections"]:
                self.assertTrue(heading.strip() and paragraphs, heading)
                self.assertTrue(all(p.strip() for p in paragraphs), heading)
            self.assertEqual(doc["sections"][-1][0], "Contact")

    def test_privacy_describes_what_the_code_really_does(self):
        text = legal.as_markdown("privacy")
        for fact in ("no telemetry", "~/.docker-gui/config.json", "0600", "keyring", "hub.docker.com",
                     "standard input", "majidaliqau@gmail.com", "Password → Delete"):
            self.assertIn(fact, text)

    def test_terms_cover_the_essentials(self):
        text = legal.as_markdown("terms")
        for fact in ("affiliated with", "Docker, Inc.", "\"as is\"", "volumes cannot be recovered",
                     "docker group", "Limit of liability", "majidaliqau@gmail.com"):
            self.assertIn(fact, text)

    def test_version_and_date_are_stated(self):
        for kind in legal.DOCUMENTS:
            self.assertIn(legal.LEGAL_VERSION, legal.as_markdown(kind))
            self.assertIn(legal.LAST_UPDATED, legal.as_markdown(kind))

    def test_readme_and_installer_point_to_the_files(self):
        self.assertIn("PRIVACY.md", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("TERMS.md", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("PRIVACY.md", (ROOT / "install.sh").read_text(encoding="utf-8"))

    def test_first_run_check_runs_before_anything_else_needs_docker(self):
        source = (ROOT / "docker_gui_modular.py").read_text(encoding="utf-8")
        self.assertLess(source.index("needs_acceptance()"), source.index("check_docker_installed()"))


class TestAcceptance(_ConfigDir):

    def test_asks_until_accepted(self):
        self.assertTrue(legal_view.needs_acceptance())
        legal_view.record_acceptance()
        self.assertFalse(legal_view.needs_acceptance())
        self.assertEqual(cm.get_setting("legal_accepted"), legal.LEGAL_VERSION)

    def test_a_new_version_asks_again(self):
        cm.set_setting("legal_accepted", "2020-01-01")
        self.assertTrue(legal_view.needs_acceptance())

    def test_unattended_setups_can_accept_through_the_environment(self):
        os.environ[legal_view.ACCEPT_ENV] = "yes"
        self.assertFalse(legal_view.needs_acceptance())
        self.assertEqual(cm.get_setting("legal_accepted"), legal.LEGAL_VERSION)

    def test_other_values_of_the_variable_do_not_count(self):
        os.environ[legal_view.ACCEPT_ENV] = "no"
        self.assertTrue(legal_view.needs_acceptance())

    def test_only_the_version_is_stored(self):
        legal_view.record_acceptance()
        saved = (self.dir / "config.json").read_text()
        self.assertIn(legal.LEGAL_VERSION, saved)
        self.assertEqual(cm.DEFAULT_SETTINGS["legal_accepted"], "")


class _Tk(_ConfigDir):
    def setUp(self):
        super().setUp()
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def find(self, widget, cls=None, text=None):
        found = []

        def walk(w):
            for child in w.winfo_children():
                try:
                    if (cls is None or child.winfo_class() == cls) and (text is None or child.cget("text") == text):
                        found.append(child)
                except tk.TclError:
                    pass
                walk(child)
        walk(widget)
        return found

    def dialog(self):
        return [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)][-1]


class TestReader(_Tk):

    def test_document_page_shows_headings_bullets_and_is_read_only(self):
        frame = legal_view.build_document(self.root, "privacy")
        text = frame.text
        content = text.get("1.0", tk.END)
        for expected in ("Privacy Policy", "What is stored on your computer", "•  your theme and settings",
                         "What is sent over the network", "majidaliqau@gmail.com"):
            self.assertIn(expected, content)
        self.assertEqual(str(text.cget("state")), "disabled")

    def test_dialog_opens_and_closes(self):
        dialog = legal_view.show_legal_dialog(self.root, "terms")
        self.root.update()
        self.assertIn("Terms of Use", dialog.title())
        self.assertIn("Limit of liability", self.find(dialog, "Text")[0].get("1.0", tk.END))
        close = self.find(dialog, "TButton", "Close")[0]
        self.assertLessEqual(close.winfo_rooty() + close.winfo_height(), dialog.winfo_rooty() + dialog.winfo_height())
        close.invoke()
        self.assertFalse(dialog.winfo_exists())


class TestFirstRun(_Tk):

    def _run(self, act):
        self.root.after(150, act)
        return legal_view.ask_first_run(self.root)

    def test_accept_needs_the_checkbox_and_is_recorded(self):
        seen = {}

        def act():
            dialog = self.dialog()
            accept = self.find(dialog, "TButton", "Accept and continue")[0]
            seen["before"] = str(accept.cget("state"))
            check = self.find(dialog, "TCheckbutton")[0]
            check.invoke()
            self.root.update()
            seen["after"] = str(accept.cget("state"))
            seen["tabs"] = [dialog.nametowidget(t) for t in self.find(dialog, "TNotebook")[0].tabs()]
            accept.invoke()
        self.assertTrue(self._run(act))
        self.assertEqual((seen["before"], seen["after"]), ("disabled", "normal"))
        self.assertEqual(len(seen["tabs"]), 2)                       # Privacy Policy and Terms of Use
        self.assertFalse(legal_view.needs_acceptance())

    def test_the_buttons_are_never_clipped(self):
        """Regression: a tall text area once pushed the checkbox and Accept / Decline out of the window."""
        seen = {}

        def act():
            dialog = self.dialog()
            dialog.update()
            bottom = dialog.winfo_rooty() + dialog.winfo_height()
            for label in ("Accept and continue", "Decline and exit"):
                button = self.find(dialog, "TButton", label)[0]
                seen[label] = button.winfo_rooty() + button.winfo_height() <= bottom
            check = self.find(dialog, "TCheckbutton")[0]
            seen["check"] = check.winfo_rooty() + check.winfo_height() <= bottom
            self.find(dialog, "TButton", "Decline and exit")[0].invoke()
        self._run(act)
        self.assertEqual(seen, {"Accept and continue": True, "Decline and exit": True, "check": True})

    def test_decline_exits_and_records_nothing(self):
        self.assertFalse(self._run(lambda: self.find(self.dialog(), "TButton", "Decline and exit")[0].invoke()))
        self.assertTrue(legal_view.needs_acceptance())

    def test_a_failed_grab_does_not_crash_the_dialog(self):
        """Tk raises "grab failed: window not viewable" when the dialog is not on screen yet."""
        real = tk.Toplevel.grab_set
        calls = []

        def flaky(widget):
            calls.append(1)
            if len(calls) < 3:
                raise tk.TclError("grab failed: window not viewable")
            return real(widget)
        with patch.object(tk.Toplevel, "grab_set", flaky):
            self.assertTrue(self._run(lambda: self._accept_via_checkbox()))
        self.assertGreaterEqual(len(calls), 1)

    def _accept_via_checkbox(self):
        dialog = self.dialog()
        self.find(dialog, "TCheckbutton")[0].invoke()
        self.root.update()
        self.find(dialog, "TButton", "Accept and continue")[0].invoke()

    def test_closing_the_window_is_declining(self):
        self.assertFalse(self._run(lambda: self.dialog().destroy()))
        self.assertTrue(legal_view.needs_acceptance())


class TestHomePageLinks(_Tk):

    def _landing(self, open_legal):
        from src.ui import landing_page, workflow_view
        sync = patch.object(workflow_view, "startThreadForTask", side_effect=lambda task: task())
        sync.start()
        self.addCleanup(sync.stop)
        self.root.deiconify()
        self.root.geometry("1000x700")
        landing = landing_page.LandingPage(
            self.root, tk.StringVar(master=self.root), [("Start", lambda: None)], lambda _c: None, ["Containers"],
            fetch_overview=lambda: UP, open_legal=open_legal)
        landing.pack(fill=tk.BOTH, expand=True)
        self.root.update()
        return landing

    def test_privacy_and_terms_are_linked_from_the_hero_and_the_footer(self):
        opened = []
        landing = self._landing(opened.append)
        for label, kind in (("Privacy Policy", "privacy"), ("Terms of Use", "terms")):
            links = self.find(landing, text=label)
            self.assertEqual(len(links), 2, label)                      # hero (top right) and footer
            for link in links:
                link.event_generate("<Button-1>")
                self.assertEqual(opened[-1], kind)

    def test_footer_names_the_author(self):
        landing = self._landing(lambda _k: None)
        texts = [w.cget("text") for w in self.find(landing, "TLabel")]
        self.assertTrue(any("Majid Ali" in t and "majidaliqau@gmail.com" in t for t in texts))

    def test_clicking_without_a_handler_does_nothing(self):
        landing = self._landing(None)
        self.find(landing, text="Privacy Policy")[0].event_generate("<Button-1>")


if __name__ == "__main__":
    unittest.main()
