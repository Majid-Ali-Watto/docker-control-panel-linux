# Privacy Policy — Docker Control Panel

_Last updated: 30 October 2026 (version 2026-10-30)_

Docker Control Panel runs entirely on your computer. It has no accounts, no analytics and no telemetry, and it sends nothing to its author. This page says what it keeps on your machine and the few times it talks to the network, so you can decide whether you are comfortable with it.

## What is stored on your computer

The app keeps one small settings file, ~/.docker-gui/config.json, readable only by you (mode 0600). It holds:

- your theme and settings (Live Stats interval, container engine, terminal, notifications);
- the paths of the Compose files you started, so those projects stay listed;
- which version of this Privacy Policy and the Terms of Use you accepted.

Your sudo password, if you choose to let the app remember it, is kept in the desktop keyring (libsecret / secret-tool) when one is available. Only without a keyring is it written to the settings file. Users in the docker group are never asked for a password. You can remove it at any time with Password → Delete in the sidebar, or by deleting the ~/.docker-gui folder.

## Temporary files

To open a shell in a container, the app writes a short launch script to your system's temporary folder. It contains no password. If a sudo password is in use, a second helper that supplies it to the terminal is written there too, readable only by you. Both are deleted within seconds.

## What is sent over the network

The app does not contact its author or any analytics service. Network traffic happens only in these cases:

- Docker itself talks to registries when you pull, push, search or log in (Docker Hub or any registry you name). That traffic is between Docker and the registry and follows the registry's own policy.
- When you search Docker Hub from the Pull dialog, the app asks Docker Hub's public API (hub.docker.com) for the size of each result, one request per result. A request contains the image name and, like any web request, your IP address.
- Links in the Creator tab (portfolio, GitHub, email) open in your browser or mail app only when you click them.

## Passwords and secrets

Your sudo password is used only to run commands with sudo on your machine. It is never logged, printed or sent anywhere. Registry passwords and tokens are handed to Docker on standard input and are not stored by the app (Docker keeps registry credentials in its own configuration, ~/.docker/config.json). Values in container environment variables that look like secrets are hidden in the Details view.

## The Docker data you look at

Container names, logs, environment, images and the like are read from your own Docker engine and shown on screen. They are not copied anywhere unless you save or export them yourself.

## Your choices

- Turn desktop notifications off in Settings.
- Remove saved data: Password → Delete, or delete ~/.docker-gui.
- Uninstall with ./uninstall.sh, which removes the desktop entry, the command and the Python environment.

## Changes to this policy

If this policy changes in a way that matters, its version date changes and the app asks you to accept it again the next time it starts.

## Contact

Majid Ali — majidaliqau@gmail.com

---

The same text is shown inside the app (Docker home page → Privacy Policy / Terms of Use) and on first start. Questions: majidaliqau@gmail.com.
