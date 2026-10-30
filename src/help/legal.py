"""
Privacy Policy and Terms of Use: one source for the in-app pages (ui/legal_view.py), the first-run
agreement, and the PRIVACY.md / TERMS.md files in the repository root.

Regenerate the markdown files after editing the text (a test fails while they differ):

    python3 -m src.help.legal

Bump LEGAL_VERSION and LAST_UPDATED when the meaning of a document changes: every user is then
asked to accept again on the next start.
"""

import os

from src.help.help_creator import APP_NAME, CREATOR_EMAIL, CREATOR_NAME

LEGAL_VERSION = "2026-10-30"
LAST_UPDATED = "30 October 2026"

# A section body is a list of paragraphs; a paragraph starting with "- " is a bullet.
DOCUMENTS = {
    "privacy": {
        "title": "Privacy Policy",
        "file": "PRIVACY.md",
        "intro": (f"{APP_NAME} runs entirely on your computer. It has no accounts, no analytics and no "
                  f"telemetry, and it sends nothing to its author. This page says what it keeps on your "
                  f"machine and the few times it talks to the network, so you can decide whether you are "
                  f"comfortable with it."),
        "sections": [
            ("What is stored on your computer", [
                "The app keeps one small settings file, ~/.docker-gui/config.json, readable only by you "
                "(mode 0600). It holds:",
                "- your theme and settings (Live Stats interval, container engine, terminal, notifications);",
                "- the paths of the Compose files you started, so those projects stay listed;",
                "- which version of this Privacy Policy and the Terms of Use you accepted.",
                "Your sudo password, if you choose to let the app remember it, is kept in the desktop keyring "
                "(libsecret / secret-tool) when one is available. Only without a keyring is it written to the "
                "settings file. Users in the docker group are never asked for a password. You can remove it "
                "at any time with Password → Delete in the sidebar, or by deleting the ~/.docker-gui folder.",
            ]),
            ("Temporary files", [
                "To open a shell in a container, the app writes a short launch script to your system's "
                "temporary folder. It contains no password. If a sudo password is in use, a second helper "
                "that supplies it to the terminal is written there too, readable only by you. Both are "
                "deleted within seconds.",
            ]),
            ("What is sent over the network", [
                "The app does not contact its author or any analytics service. Network traffic happens "
                "only in these cases:",
                "- Docker itself talks to registries when you pull, push, search or log in (Docker Hub or "
                "any registry you name). That traffic is between Docker and the registry and follows the "
                "registry's own policy.",
                "- When you search Docker Hub from the Pull dialog, the app asks Docker Hub's public API "
                "(hub.docker.com) for the size of each result, one request per result. A request contains "
                "the image name and, like any web request, your IP address.",
                "- Links in the Creator tab (portfolio, GitHub, email) open in your browser or mail app only "
                "when you click them.",
            ]),
            ("Passwords and secrets", [
                "Your sudo password is used only to run commands with sudo on your machine. It is never "
                "logged, printed or sent anywhere. Registry passwords and tokens are handed to Docker on "
                "standard input and are not stored by the app (Docker keeps registry credentials in its own "
                "configuration, ~/.docker/config.json). Values in container environment variables that look "
                "like secrets are hidden in the Details view.",
            ]),
            ("The Docker data you look at", [
                "Container names, logs, environment, images and the like are read from your own Docker "
                "engine and shown on screen. They are not copied anywhere unless you save or export them "
                "yourself.",
            ]),
            ("Your choices", [
                "- Turn desktop notifications off in Settings.",
                "- Remove saved data: Password → Delete, or delete ~/.docker-gui.",
                "- Uninstall with ./uninstall.sh, which removes the desktop entry, the command and the "
                "Python environment.",
            ]),
            ("Changes to this policy", [
                "If this policy changes in a way that matters, its version date changes and the app asks "
                "you to accept it again the next time it starts.",
            ]),
            ("Contact", [f"{CREATOR_NAME} — {CREATOR_EMAIL}"]),
        ],
    },
    "terms": {
        "title": "Terms of Use",
        "file": "TERMS.md",
        "intro": (f"These terms apply to {APP_NAME}, a graphical front end for Docker on Linux. By installing "
                  f"or using it you agree to them. If you do not agree, do not use it (the app asks you to "
                  f"accept on first start and exits if you decline)."),
        "sections": [
            ("What the app is", [
                f"{APP_NAME} builds Docker commands from your clicks, runs them on your computer and shows "
                f"the result. It is created by {CREATOR_NAME}. It is an independent project and is not "
                f"affiliated with, endorsed by or sponsored by Docker, Inc. Docker and the Docker logo are "
                f"trademarks of Docker, Inc.",
            ]),
            ("You are in control, and responsible", [
                "The app can stop, remove and delete things. Stop All, Delete All, Prune and Clean All remove "
                "containers, images, volumes and networks, and deleted volumes cannot be recovered. Read the "
                "confirmation before you accept it, and keep backups of data you care about.",
                "Every command runs with your own permissions, or with sudo. Membership of the docker group "
                "is equivalent to root access on most systems, so use the app only on computers and accounts "
                "you are allowed to administer.",
            ]),
            ("No warranty", [
                f"{APP_NAME} is provided \"as is\" and \"as available\", without warranty of any kind, "
                "express or implied, including fitness for a particular purpose and non-infringement. "
                "There is no promise that it is error-free, that it works with every Docker setup, or "
                "that the information it shows is complete or current.",
            ]),
            ("Limit of liability", [
                f"To the fullest extent the law allows, {CREATOR_NAME} is not liable for any loss or damage "
                "arising from the use of, or inability to use, the app, including lost data, lost or "
                "interrupted services, or damage to systems, even if told that such loss was possible.",
            ]),
            ("Third-party software and services", [
                "The app relies on software and services it does not control: Docker Engine and CLI (or "
                "Podman), Python, Tkinter, ttkbootstrap, Pillow, Docker Hub and any registry you use. Their "
                "own licences and terms apply to them. If you use Docker Desktop, its subscription terms "
                "apply to Docker Desktop, not to this app.",
            ]),
            ("Ownership", [
                f"{APP_NAME} was created by {CREATOR_NAME}. Rights in the source code are governed by the "
                "licence published with the project repository, where one is provided.",
            ]),
            ("Changes to these terms", [
                "If these terms change in a way that matters, their version date changes and the app asks "
                "you to accept them again on its next start. Continuing to use the app after that means you "
                "accept the new terms.",
            ]),
            ("Contact", [f"{CREATOR_NAME} — {CREATOR_EMAIL}"]),
        ],
    },
}


def as_markdown(kind):
    """The document as the markdown file shipped in the repository root."""
    doc = DOCUMENTS[kind]
    lines = [f"# {doc['title']} — {APP_NAME}", "", f"_Last updated: {LAST_UPDATED} (version {LEGAL_VERSION})_", "",
             doc["intro"], ""]
    for heading, paragraphs in doc["sections"]:
        lines += [f"## {heading}", ""]
        previous_bullet = False
        for paragraph in paragraphs:
            bullet = paragraph.startswith("- ")
            if not bullet and previous_bullet:
                lines.append("")
            lines.append(paragraph)
            if not bullet:
                lines.append("")
            previous_bullet = bullet
        if previous_bullet:
            lines.append("")
    lines += ["---", "",
              f"The same text is shown inside the app (Docker home page → Privacy Policy / Terms of Use) and "
              f"on first start. Questions: {CREATOR_EMAIL}.", ""]
    return "\n".join(lines)


def write_markdown_files(root=None):
    """Write PRIVACY.md and TERMS.md into the repository root; returns the paths."""
    root = root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    paths = []
    for kind, doc in DOCUMENTS.items():
        path = os.path.join(root, doc["file"])
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(as_markdown(kind))
        paths.append(path)
    return paths


if __name__ == "__main__":
    for written in write_markdown_files():
        print("wrote", written)
