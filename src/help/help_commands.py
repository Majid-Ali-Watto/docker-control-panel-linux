"""
Docker commands reference shown in the Commands tab.

Two sets:
  * APP_COMMAND_SECTIONS: what this app runs. Built from the constants in src/docker/commands.py
    (grouped by that file's section comments, described in _DESCRIPTIONS) plus the few commands
    that are issued inline elsewhere (_EXTRA_APP_COMMANDS). A constant without a description
    fails the tests, so a new command cannot be forgotten here.
  * COMMAND_SECTIONS: a general docker reference.
`commands_as_text()` flattens both for "Copy all" / "Download".
"""

import re
from pathlib import Path

from src.docker import commands as _commands


# Constants whose templates are awkward to read as built: shown as an equivalent full command
_DISPLAY_OVERRIDES = {
    "DOCKER_IMAGE_BUILD": "docker build -t <name:tag> -f <Dockerfile> --build-arg KEY=value <context>",
    "DOCKER_RUN_DETACHED": ("docker run -d --restart <policy> --name <name> -p <host>:<container> -e KEY=value "
                            "-v <host_path>:<container_path> --network <network> <image> <command>"),
    "DOCKER_NETWORK_CREATE": "docker network create --driver <driver> [--subnet <cidr>] <name>",
    "DOCKER_CONTAINER_LOGS": "docker logs [-t] --tail <lines> <container>",
    "DOCKER_CONTAINER_LOGS_FOLLOW": "docker logs [-t] --tail <lines> --follow <container>",
    "DOCKER_EVENTS": ("docker events --since <time> [--filter type=<type>] "
                      "--format '{{.Time}}\\t{{.Type}}\\t{{.Action}}\\t{{.Actor.ID}}\\t{{.Actor.Attributes.name}}'"),
    "DOCKER_LOGIN": "docker login -u <username> --password-stdin [<registry>]",
    "DOCKER_LOGOUT": "docker logout [<registry>]",
}

_DESCRIPTIONS = {
    # System
    "DOCKER_DISK_STORAGE_SIMPLE": "Disk usage summary (Stats → Docker Disk Storage)",
    "DOCKER_DISK_USAGE_VERBOSE": "Detailed disk usage per image, container and volume (Disk Usage tabs)",
    "DOCKER_SYSTEM_PRUNE": "Remove stopped containers, dangling images and unused networks",
    "DOCKER_INFO": "Daemon and host details: storage driver, cgroups, root dir (System → Info)",
    "DOCKER_VERSION": "Client and server versions (System → Info)",
    "DOCKER_BUILDX_LS": "List buildx builders and their platforms (System → Builders)",
    "DOCKER_BUILDER_PRUNE": "Remove the build cache (System → Prune Build Cache)",
    # Contexts
    "DOCKER_CONTEXT_LS": "List contexts: local and remote engines (System → Contexts)",
    "DOCKER_CONTEXT_USE": "Switch the active context (System → Contexts → Use)",
    "DOCKER_CONTEXT_INSPECT": "Show a context's details (System → Contexts → Inspect)",
    # Events
    "DOCKER_EVENTS": "Stream daemon events live (System → Events)",
    # Container lists
    "DOCKER_PS_RUNNING": "List running containers (Containers → Running)",
    "DOCKER_PS_ALL": "List all containers (Containers → All)",
    "DOCKER_PS_STOPPED": "List stopped containers (Containers → Stopped)",
    "DOCKER_PS_PAUSED": "List paused containers (Containers → Paused)",
    "DOCKER_PS_IDS_ALL": "IDs of all containers (used by the bulk actions)",
    "DOCKER_PS_IDS_RUNNING": "IDs of running containers",
    "DOCKER_PS_NAMES_ALL": "Names of all containers (network connect / rename dialogs)",
    # Stats
    "DOCKER_STATS_NO_STREAM": "One-time CPU / memory / network / block I/O snapshot of running containers (Stats)",
    # Container actions
    "DOCKER_START_ALL": "Start every container (Containers → Start All)",
    "DOCKER_STOP_ALL": "Stop every container (Containers → Stop All)",
    "DOCKER_RESTART_ALL": "Restart every container (Containers → Restart All)",
    "DOCKER_RM_ALL": "Force-remove every container (Containers → Delete All)",
    "DOCKER_STOP_ALL_SAFE": "Stop every container, ignoring errors (Docker → Clean All)",
    "DOCKER_RM_ALL_SAFE": "Remove every container, ignoring errors (Docker → Clean All)",
    "DOCKER_CONTAINER_START": "Start the selected container(s)",
    "DOCKER_CONTAINER_STOP": "Stop the selected container(s)",
    "DOCKER_CONTAINER_RESTART": "Restart the selected container(s)",
    "DOCKER_CONTAINER_RM": "Force-remove the selected container(s)",
    "DOCKER_CONTAINER_PAUSE": "Pause the selected container(s)",
    "DOCKER_CONTAINER_UNPAUSE": "Unpause the selected container(s)",
    "DOCKER_CONTAINER_RENAME": "Rename a container",
    "DOCKER_CONTAINER_COMMIT": "Create an image from a container",
    "DOCKER_CONTAINER_INSPECT": "Show a container's details (JSON)",
    "DOCKER_CONTAINER_LOGS": "Show a container's last log lines (Logs, optionally with timestamps)",
    "DOCKER_CONTAINER_LOGS_FOLLOW": "Follow a container's logs live (Logs → Follow)",
    "DOCKER_CONTAINER_TOP": "List the processes running in a container (Processes)",
    "DOCKER_CONTAINER_DIFF": "Files a container added, changed or deleted (Changes)",
    "DOCKER_CONTAINER_EXPORT": "Export a container's filesystem to a tar file (Export)",
    "DOCKER_EXEC_LS": "List a folder inside a container (file browser)",
    "DOCKER_CP_FROM": "Copy a file from a container to this machine (file browser)",
    "DOCKER_CP_TO": "Copy a file from this machine into a container (file browser)",
    # Images
    "DOCKER_IMAGES_ALL": "List images (Images → All)",
    "DOCKER_IMAGES_DANGLING": "List untagged (dangling) images (Images → Dangling)",
    "DOCKER_IMAGES_IDS_ALL": "IDs of all images (used by the bulk actions)",
    "DOCKER_RMI_ALL": "Force-remove every image (Images → Delete All)",
    "DOCKER_RMI_ALL_SAFE": "Remove every image, ignoring errors (Docker → Clean All)",
    "DOCKER_IMAGE_RM": "Force-remove the selected image(s)",
    "DOCKER_IMAGE_PRUNE": "Remove dangling (untagged) images (Images → Prune)",
    "DOCKER_IMAGE_TAG": "Add a tag to an image",
    "DOCKER_IMAGE_SAVE": "Save an image to a tar file",
    "DOCKER_IMAGE_LOAD": "Load an image from a tar file (Images → Load)",
    "DOCKER_IMAGE_IMPORT": "Create an image from an exported container tar (Images → Import)",
    "DOCKER_SCOUT_CVES": "Scan an image for known vulnerabilities (Scan; trivy is used when scout is missing)",
    "DOCKER_IMAGE_BUILD": "Build an image from a Dockerfile (Images → Build)",
    "DOCKER_IMAGE_HISTORY": "Show an image's layer history",
    "DOCKER_IMAGE_INSPECT": "Show an image's details (JSON)",
    # Volumes
    "DOCKER_VOLUME_LS_IDS": "Names of all volumes",
    "DOCKER_VOLUME_LS_DANGLING": "Names of volumes no container uses",
    "DOCKER_VOLUME_PRUNE": "Remove unused volumes (Volumes → Prune)",
    "DOCKER_VOLUME_RM_ALL": "Remove every volume (Volumes → Delete All)",
    "DOCKER_VOLUME_RM_ALL_SAFE": "Remove every volume, ignoring errors (Docker → Clean All)",
    "DOCKER_VOLUME_CREATE": "Create a volume (Volumes → Create)",
    "DOCKER_VOLUME_RM": "Remove the selected volume(s)",
    "DOCKER_VOLUME_INSPECT": "Show a volume's details (JSON)",
    # Networks
    "DOCKER_NETWORK_LS": "List networks (Networks)",
    "DOCKER_NETWORK_NAMES": "Names of all networks (connect dialog)",
    "DOCKER_NETWORK_CREATE": "Create a network (Networks → Create)",
    "DOCKER_NETWORK_RM": "Remove the selected network(s)",
    "DOCKER_NETWORK_INSPECT": "Show a network's details (JSON)",
    "DOCKER_NETWORK_PRUNE": "Remove unused networks (Networks → Prune)",
    "DOCKER_NETWORK_CONNECT": "Attach a container to a network",
    "DOCKER_NETWORK_DISCONNECT": "Detach a container from a network",
    # Compose
    "DOCKER_COMPOSE_LS": "List Compose projects (Compose)",
    "DOCKER_COMPOSE_PS": "List a project's services, including stopped ones",
    "DOCKER_COMPOSE_UP": "Start a project in the background (Compose → Up From File)",
    "DOCKER_COMPOSE_UP_BUILD": "Rebuild images, then start a project",
    "DOCKER_COMPOSE_BUILD": "Build a project's images",
    "DOCKER_COMPOSE_PULL": "Pull a project's images",
    "DOCKER_COMPOSE_STOP": "Stop a project without removing it",
    "DOCKER_COMPOSE_DOWN": "Stop and remove a project's containers and networks",
    "DOCKER_COMPOSE_DOWN_VOLUMES": "Down, and also remove the project's named volumes",
    "DOCKER_COMPOSE_RESTART": "Restart a project's services",
    "DOCKER_COMPOSE_LOGS": "Show a project's last log lines",
    "DOCKER_COMPOSE_LOGS_FOLLOW": "Follow a project's logs live (Compose Logs → Follow)",
    "DOCKER_COMPOSE_CONFIG": "Show the final merged Compose configuration",
    # Inspect
    "DOCKER_INSPECT_IMAGE": "Get the image ID a container was created from",
    "DOCKER_INSPECT_MOUNTS": "Get a container's mounts as JSON (used to find its volumes)",
    "DOCKER_INSPECT_ANCESTOR": "IDs of containers created from an image (used by Stop Using / Delete)",
    # Registry
    "DOCKER_LOGIN": "Log in to a registry; the password is sent on stdin (Images → Registry)",
    "DOCKER_LOGOUT": "Log out of a registry (Images → Registry)",
    # Pull / push
    "DOCKER_PULL": "Download an image (Images → Pull)",
    "DOCKER_IMAGE_PUSH": "Upload an image to a registry (Images → Push)",
    "DOCKER_SEARCH": "Search Docker Hub (Images → Search Hub)",
    # Run
    "DOCKER_RUN_DETACHED": "Create and start a container from an image (Images → Run)",
}

# Commands the app issues inline (not in commands.py): group -> [(command, description)]
_EXTRA_APP_COMMANDS = {
    "Service": [
        ("systemctl is-active docker", "Check whether the Docker service is running (sidebar status)"),
        ("systemctl start docker.socket docker.service", "Start the Docker service (Docker → Start)"),
        ("systemctl stop docker.socket docker.service", "Stop the Docker service (Docker → Stop)"),
        ("systemctl restart docker.socket docker.service", "Restart the Docker service (Docker → Restart)"),
        ("which docker", "Check that Docker is installed at startup"),
        ("docker info --format '{{.ServerVersion}}'", "Check whether sudo is needed at all (user is in the docker group)"),
        ("sudo -S <command>", "How every command above is run: the saved sudo password is sent on stdin"),
    ],
    "Container actions": [
        ("docker exec -it <container> /bin/sh", "Open a shell inside a container (Terminal action)"),
        ("docker logs [-t] --follow <container>", "Follow a container's logs live (Logs → Follow)"),
        ("docker inspect --format='{{.State.Status}}' <container>", "Get a container's state (Logs / Terminal)"),
    ],
    "Compose": [
        ("docker rm -f <container_ids>", "Remove leftover containers of a Compose project"),
    ],
    "Registry": [
        ('cat "${DOCKER_CONFIG:-$HOME/.docker}/config.json"', "Read which registries are logged in (Images → Registry)"),
    ],
    "Images": [
        ("trivy image <image>", "Vulnerability scan when docker scout is not installed (Images → Scan)"),
    ],
    "Install Docker": [
        ("sudo apt-get install -y docker-ce docker-ce-cli containerd.io", "Install Docker Engine (install prompt)"),
        ("sudo apt-get install docker.io", "Alternative: install Docker from the Ubuntu repository"),
        ("sudo systemctl enable docker", "Start Docker at boot (install prompt)"),
        ("sudo apt install tilix", "Install a terminal emulator for the Container Terminal action"),
    ],
}

_GROUP_TITLES = {   # commands.py section comment -> title shown in the tab
    "System": "System", "Container list": "Container lists", "Container stats": "Container stats",
    "Container actions": "Container actions", "Image": "Images", "Volume": "Volumes",
    "Network": "Networks", "Compose": "Compose", "Inspect": "Inspect", "Pull / push": "Pull / push / search",
    "Run": "Run", "Context": "Contexts", "Events": "Events", "Registry": "Registry",
}


def _display_template(name, template):
    """A commands.py template as a readable command: {name} -> <name>, {{{{x}}}} -> {{x}}."""
    if name in _DISPLAY_OVERRIDES:
        return _DISPLAY_OVERRIDES[name]
    text = template.replace("{{{{", "\x00").replace("}}}}", "\x01").replace("{{", "\x00").replace("}}", "\x01")
    text = text.replace("{files}", "-f <file.yml>")
    text = re.sub(r"\{(\w+)\}", r"<\1>", text)
    return text.replace("\x00", "{{").replace("\x01", "}}").replace("\t", "\\t")


def _display_variants(name, template, description):
    """[(command, description)] for one constant. Compose templates take `{files}`: they are listed
    first as typed inside the project folder (no -f needed) and then with an explicit compose file."""
    shown = _display_template(name, template)
    if "{files}" not in template:
        return [(shown, description)]
    in_folder = _display_template(name, template.replace(" {files}", ""))
    return [(in_folder, f"{description} — run in the project folder"),
            (shown, f"{description} — with a compose file")]


def _app_constant_groups():
    """[(group title, [constant names])] in the order commands.py declares them."""
    groups, current = [], None
    for line in Path(_commands.__file__).read_text(encoding="utf-8").splitlines():
        header = re.match(r"# (.+?)( commands?)?$", line)
        if header and "templates" not in line:
            current = _GROUP_TITLES.get(header.group(1), header.group(1))
            groups.append((current, []))
            continue
        constant = re.match(r"([A-Z][A-Z0-9_]*) = ", line)
        if constant and groups:
            groups[-1][1].append(constant.group(1))
    return groups


def _build_app_sections():
    sections = {}
    for title, names in _app_constant_groups():
        items = sections.setdefault(title, [])
        for name in names:
            items.extend(_display_variants(name, getattr(_commands, name), _DESCRIPTIONS.get(name, "")))
    for title, items in _EXTRA_APP_COMMANDS.items():
        sections.setdefault(title, []).extend(items)
    return [(title.upper(), items) for title, items in sections.items()]


# (title, [(command, description)]) — see the module docstring
APP_COMMAND_SECTIONS = _build_app_sections()


COMMAND_SECTIONS = [
    ("SERVICE", [
        ("systemctl start docker", "Start the Docker service"),
        ("systemctl stop docker", "Stop the Docker service"),
        ("systemctl restart docker", "Restart the Docker service"),
        ("systemctl reload docker", "Reload the daemon configuration without restarting containers"),
        ("systemctl status docker", "Show whether Docker is running and its recent log lines"),
        ("systemctl is-active docker", "Print active / inactive (handy in scripts)"),
        ("systemctl start docker.socket docker.service", "Start the socket and the service (what this app does)"),
        ("systemctl stop docker.socket docker.service", "Stop both, so the socket does not restart Docker"),
        ("systemctl enable docker", "Start Docker automatically at boot"),
        ("systemctl enable --now docker", "Enable at boot and start it right now"),
        ("systemctl disable docker", "Do not start Docker at boot"),
        ("systemctl is-enabled docker", "Check whether Docker starts at boot"),
        ("systemctl daemon-reload", "Reload systemd after editing the Docker unit files"),
        ("journalctl -u docker", "Show the Docker daemon log"),
        ("journalctl -u docker -f", "Follow the Docker daemon log live"),
        ("journalctl -u docker --since \"1 hour ago\"", "Daemon log of the last hour"),
        ("sudo usermod -aG docker $USER", "Allow your user to run docker without sudo (log out and in again)"),
        ("newgrp docker", "Apply the docker group in the current shell without logging out"),
        ("docker --version", "Show the Docker client version"),
    ]),
    ("CONTAINERS", [
        # list
        ("docker ps", "List running containers"),
        ("docker ps -a", "List all containers (including stopped)"),
        ("docker ps -q", "List only the IDs of running containers"),
        ("docker ps -aq", "List only the IDs of all containers"),
        ("docker ps -l", "Show the most recently created container"),
        ("docker ps -n <n>", "Show the n most recently created containers"),
        ("docker ps -s", "Show container sizes"),
        ("docker ps --no-trunc", "Do not shorten IDs and commands"),
        ("docker ps -a --filter status=exited", "List stopped containers"),
        ("docker ps -a --filter status=paused", "List paused containers"),
        ("docker ps -a --filter status=created", "List containers that were created but never started"),
        ("docker ps -a --filter status=restarting", "List containers that are restarting"),
        ("docker ps -a --filter name=<name>", "Find containers by name"),
        ("docker ps -a --filter ancestor=<image>", "List containers created from an image"),
        ("docker ps -a --filter label=<key=value>", "Find containers by label"),
        ("docker ps --filter health=unhealthy", "List containers failing their health check"),
        ("docker ps --format 'table {{.ID}}\\t{{.Names}}\\t{{.Status}}'", "List with chosen columns"),
        ("docker container ls", "Same as docker ps"),
        ("docker container ls -a", "Same as docker ps -a"),
        # run / create
        ("docker run <image>", "Create and start a container (foreground)"),
        ("docker run -d <image>", "Create and start a container in the background"),
        ("docker run -d --name <name> <image>", "Run in the background with a name"),
        ("docker run -it --rm <image> sh", "Run a throw-away interactive container"),
        ("docker run --rm <image> <command>", "Run one command in a new container, then delete it"),
        ("docker run -d -p <host>:<container> <image>", "Publish a container port on the host"),
        ("docker run -d -p 127.0.0.1:<host>:<container> <image>", "Publish a port only on localhost"),
        ("docker run -d -P <image>", "Publish all exposed ports on random host ports"),
        ("docker run -d -e KEY=value <image>", "Set an environment variable"),
        ("docker run -d --env-file <file.env> <image>", "Set environment variables from a file"),
        ("docker run -d -v <host_path>:<container_path> <image>", "Mount a host folder (bind mount)"),
        ("docker run -d -v <volume>:<container_path> <image>", "Mount a named volume"),
        ("docker run -d -v <host_path>:<container_path>:ro <image>", "Mount read-only"),
        ("docker run -d --mount type=bind,src=<host_path>,dst=<container_path> <image>", "Mount with the explicit --mount syntax"),
        ("docker run -d --network <network> <image>", "Attach to a network"),
        ("docker run -d --restart always <image>", "Always restart the container (also after a reboot)"),
        ("docker run -d --restart unless-stopped <image>", "Restart unless you stopped it yourself"),
        ("docker run -d --restart on-failure:<n> <image>", "Restart on failure, at most n times"),
        ("docker run -d --memory 512m --cpus 1.5 <image>", "Limit memory and CPU"),
        ("docker run -d -w <dir> <image>", "Set the working directory"),
        ("docker run -d -u <user> <image>", "Run as a specific user"),
        ("docker run -d --hostname <name> <image>", "Set the container hostname"),
        ("docker run -it --entrypoint <command> <image>", "Override the image entrypoint"),
        ("docker run -d --read-only <image>", "Make the root filesystem read-only"),
        ("docker run -d --privileged <image>", "Give the container extended privileges (use with care)"),
        ("docker run --pull always <image>", "Always pull the image first"),
        ("docker create --name <name> <image>", "Create a container without starting it"),
        # lifecycle
        ("docker start <container>", "Start a stopped container"),
        ("docker start -a <container>", "Start and attach to its output"),
        ("docker start -ai <container>", "Start and attach interactively"),
        ("docker stop <container>", "Stop a running container"),
        ("docker stop -t <seconds> <container>", "Stop, waiting this many seconds before killing"),
        ("docker restart <container>", "Restart a container"),
        ("docker restart -t <seconds> <container>", "Restart, waiting this many seconds before killing"),
        ("docker kill <container>", "Send SIGKILL to a running container"),
        ("docker kill -s <signal> <container>", "Send a specific signal"),
        ("docker pause <container>", "Pause all processes in a container"),
        ("docker unpause <container>", "Resume a paused container"),
        ("docker rename <old> <new>", "Rename a container"),
        ("docker wait <container>", "Block until a container stops, then print its exit code"),
        ("docker update --restart unless-stopped <container>", "Change a container's restart policy"),
        ("docker update --memory <size> --cpus <n> <container>", "Change a running container's limits"),
        # remove
        ("docker rm <container>", "Remove a stopped container"),
        ("docker rm -f <container>", "Force-remove a running container"),
        ("docker rm -v <container>", "Remove a container and its anonymous volumes"),
        ("docker rm $(docker ps -aq --filter status=exited)", "Remove all stopped containers"),
        ("docker container prune", "Remove all stopped containers (asks first)"),
        ("docker container prune -f", "Remove all stopped containers without asking"),
        ("docker container prune --filter until=<24h>", "Remove stopped containers older than a time"),
        # bulk
        ("docker start $(docker ps -aq)", "Start every container"),
        ("docker stop $(docker ps -aq)", "Stop every container"),
        ("docker restart $(docker ps -aq)", "Restart every container"),
        ("docker pause $(docker ps -q)", "Pause every running container"),
        ("docker rm -f $(docker ps -aq)", "Force-remove every container"),
        # inside a container
        ("docker exec -it <container> bash", "Open a bash shell in a container"),
        ("docker exec -it <container> sh", "Open a sh shell in a container"),
        ("docker exec -it <container> /bin/sh", "Open a /bin/sh shell (what the app's Terminal action runs)"),
        ("docker exec <container> <command>", "Run a command in a running container"),
        ("docker exec <container> ls -la <path>", "List files inside a container"),
        ("docker exec -u <user> -it <container> sh", "Open a shell as another user"),
        ("docker exec -w <dir> <container> <command>", "Run a command in a specific directory"),
        ("docker exec -e KEY=value <container> <command>", "Run a command with an extra environment variable"),
        ("docker attach <container>", "Attach to a running container's main process"),
        # logs & inspection
        ("docker logs <container>", "View container logs"),
        ("docker logs -f <container>", "Follow logs live"),
        ("docker logs --tail 100 <container>", "View the last 100 log lines"),
        ("docker logs -f --tail 100 <container>", "Follow, starting from the last 100 lines"),
        ("docker logs -t <container>", "View logs with timestamps"),
        ("docker logs --since <time> <container>", "Logs since a time, e.g. 10m or 2025-01-31T10:00:00"),
        ("docker logs --until <time> <container>", "Logs before a time"),
        ("docker inspect <container>", "Show detailed container metadata (JSON)"),
        ("docker inspect --format='{{.State.Status}}' <container>", "Get the container's state"),
        ("docker inspect --format='{{.NetworkSettings.IPAddress}}' <container>", "Get the container's IP address"),
        ("docker inspect --format='{{json .Mounts}}' <container>", "Get its mounts as JSON"),
        ("docker inspect --format='{{.Config.Image}}' <container>", "Get the image it was created from"),
        ("docker inspect -s <container>", "Include the container's file size"),
        ("docker diff <container>", "Show files changed in a container's filesystem"),
        ("docker port <container>", "Show a container's published ports"),
        ("docker port <container> <container_port>", "Show the host port for one container port"),
        ("docker top <container>", "Show processes running inside a container"),
        ("docker stats", "Show live resource usage of running containers"),
        ("docker stats --no-stream", "Show a one-time snapshot of resource usage"),
        ("docker stats <container>", "Show live usage of one container"),
        ("docker stats -a", "Include stopped containers"),
        # files & images
        ("docker cp <container>:<src> <dest>", "Copy files from a container to the host"),
        ("docker cp <src> <container>:<dest>", "Copy files from the host to a container"),
        ("docker commit <container> <image:tag>", "Create a new image from a container"),
        ("docker commit -m \"<message>\" -a \"<author>\" <container> <image:tag>", "Commit with a message and author"),
        ("docker export -o <file.tar> <container>", "Export a container's filesystem to a tar archive"),
    ]),
    ("IMAGES", [
        # list
        ("docker images", "List all local images"),
        ("docker images -a", "Include intermediate images"),
        ("docker images -q", "List only image IDs"),
        ("docker images -aq", "List only the IDs of all images"),
        ("docker images --no-trunc", "Show full image IDs"),
        ("docker images --digests", "Show image digests"),
        ("docker images <repository>", "List images of one repository"),
        ("docker images --filter dangling=true", "List dangling (untagged) images"),
        ("docker images --filter reference=<name>", "List images matching a name or pattern"),
        ("docker images --filter before=<image>", "List images created before another image"),
        ("docker images --format 'table {{.Repository}}\\t{{.Tag}}\\t{{.Size}}'", "List with chosen columns"),
        ("docker image ls", "Same as docker images"),
        ("docker image ls -a", "Same as docker images -a"),
        # get
        ("docker pull <image>", "Download an image from Docker Hub"),
        ("docker pull <image>:<tag>", "Download a specific image tag"),
        ("docker pull <image>@<digest>", "Download an exact image by digest"),
        ("docker pull -a <image>", "Download all tags of an image"),
        ("docker pull --platform <os/arch> <image>", "Download for another platform, e.g. linux/arm64"),
        ("docker search <term>", "Search Docker Hub for images"),
        ("docker search --limit <n> <term>", "Limit the number of results"),
        ("docker search --filter is-official=true <term>", "Only official images"),
        ("docker search --filter stars=<n> <term>", "Only images with at least n stars"),
        ("docker search --no-trunc <term>", "Show full descriptions"),
        ("docker login", "Log in to Docker Hub"),
        ("docker login <registry>", "Log in to another registry"),
        ("docker login -u <user>", "Log in with a username (asks for the password)"),
        ("docker logout", "Log out from a registry"),
        # share
        ("docker push <image>", "Push a local image to a registry"),
        ("docker push <image>:<tag>", "Push one tag"),
        ("docker push -a <image>", "Push all tags of an image"),
        ("docker tag <source> <target>", "Create a new tag for an existing image"),
        # build
        ("docker build .", "Build an image from the Dockerfile in this folder"),
        ("docker build -t <name:tag> <context>", "Build and tag an image"),
        ("docker build -t <name:tag> -f <Dockerfile> .", "Build using a specific Dockerfile path"),
        ("docker build --build-arg KEY=value -t <name:tag> .", "Pass build-time variables to a Dockerfile"),
        ("docker build --no-cache -t <name:tag> .", "Build without using the layer cache"),
        ("docker build --pull -t <name:tag> .", "Always pull newer base images"),
        ("docker build --target <stage> -t <name:tag> .", "Build only up to a multi-stage target"),
        ("docker build --platform <os/arch> -t <name:tag> .", "Build for another platform"),
        ("docker build -q .", "Build quietly and print only the image ID"),
        ("docker buildx build --platform linux/amd64,linux/arm64 -t <image> --push .", "Build for several platforms and push (needs the buildx plugin)"),
        # move
        ("docker save -o <archive.tar> <image>", "Export an image to a tar archive"),
        ("docker save <image> | gzip > <archive.tar.gz>", "Export and compress an image"),
        ("docker load -i <archive.tar>", "Import an image from a tar archive"),
        ("docker load < <archive.tar>", "Import an image from standard input"),
        ("docker import <file.tar> <image:tag>", "Create an image from an exported filesystem"),
        # inspect
        ("docker image inspect <image>", "Show detailed image metadata (JSON)"),
        ("docker image inspect --format='{{.Size}}' <image>", "Show one field, here the size in bytes"),
        ("docker history <image>", "Show layer history of an image"),
        ("docker history --no-trunc <image>", "Show full layer commands"),
        # remove
        ("docker rmi <image>", "Remove an image"),
        ("docker rmi -f <image>", "Force-remove an image"),
        ("docker image rm <image>", "Same as docker rmi"),
        ("docker rmi -f $(docker images -aq)", "Force-remove every image"),
        ("docker rmi $(docker images --filter dangling=true -q)", "Remove all dangling images"),
        ("docker image prune", "Remove dangling images (asks first)"),
        ("docker image prune -f", "Remove dangling (untagged) images without asking"),
        ("docker image prune -a", "Remove all unused images"),
        ("docker image prune -a --filter until=<24h>", "Remove unused images older than a time"),
    ]),
    ("VOLUMES", [
        ("docker volume ls", "List all volumes"),
        ("docker volume ls -q", "List only volume names"),
        ("docker volume ls --filter dangling=true", "List volumes not used by any container"),
        ("docker volume ls -qf dangling=true", "List only the names of unused volumes"),
        ("docker volume ls --filter name=<name>", "Find volumes by name"),
        ("docker volume ls --filter driver=<driver>", "Find volumes by driver"),
        ("docker volume ls --format 'table {{.Name}}\\t{{.Driver}}'", "List with chosen columns"),
        ("docker volume create <name>", "Create a named volume"),
        ("docker volume create --driver <driver> <name>", "Create a volume with a specific driver"),
        ("docker volume create --label <key=value> <name>", "Create a labelled volume"),
        ("docker volume inspect <name>", "Show volume details (JSON)"),
        ("docker volume inspect --format='{{.Mountpoint}}' <name>", "Show where the volume lives on the host"),
        ("docker volume rm <name>", "Remove a volume"),
        ("docker volume rm -f <name>", "Remove a volume, ignoring errors if it does not exist"),
        ("docker volume rm $(docker volume ls -q)", "Remove every volume"),
        ("docker volume rm $(docker volume ls -qf dangling=true)", "Remove every unused volume"),
        ("docker volume prune", "Remove unused local volumes (asks first)"),
        ("docker volume prune -f", "Remove unused local volumes without asking"),
        ("docker volume prune -a", "Remove all unused volumes, including named ones"),
        ("docker volume prune --filter label=<key=value>", "Remove only unused volumes with a label"),
        ("docker run --rm -v <volume>:/data -v $(pwd):/backup alpine tar czf /backup/<file>.tar.gz -C /data .", "Back up a volume to a tar.gz in this folder"),
        ("docker run --rm -v <volume>:/data -v $(pwd):/backup alpine tar xzf /backup/<file>.tar.gz -C /data", "Restore a volume from a tar.gz"),
        ("docker ps -a --filter volume=<volume>", "List containers using a volume"),
    ]),
    ("NETWORKS", [
        ("docker network ls", "List all networks"),
        ("docker network ls -q", "List only network IDs"),
        ("docker network ls --no-trunc", "Show full network IDs"),
        ("docker network ls --filter driver=bridge", "List networks of one driver"),
        ("docker network ls --filter name=<name>", "Find networks by name"),
        ("docker network ls --format 'table {{.Name}}\\t{{.Driver}}\\t{{.Scope}}'", "List with chosen columns"),
        ("docker network create <name>", "Create a bridge network"),
        ("docker network create --driver bridge <name>", "Create a bridge network explicitly"),
        ("docker network create --driver overlay <name>", "Create an overlay network (Swarm)"),
        ("docker network create --driver macvlan <name>", "Create a macvlan network"),
        ("docker network create --subnet <cidr> <name>", "Create a network with a custom subnet"),
        ("docker network create --subnet <cidr> --gateway <ip> <name>", "Custom subnet and gateway"),
        ("docker network create --ip-range <cidr> --subnet <cidr> <name>", "Allocate container addresses from a smaller range"),
        ("docker network create --internal <name>", "Create a network without outside access"),
        ("docker network create --attachable <name>", "Let standalone containers attach to an overlay network"),
        ("docker network create --label <key=value> <name>", "Create a labelled network"),
        ("docker network inspect <name>", "Show network details (JSON)"),
        ("docker network inspect --format='{{json .Containers}}' <name>", "List the containers attached to a network"),
        ("docker network connect <network> <container>", "Attach a container to a network"),
        ("docker network connect --ip <address> <network> <container>", "Attach with a fixed IP address"),
        ("docker network connect --alias <alias> <network> <container>", "Attach with a network alias"),
        ("docker network disconnect <network> <container>", "Detach a container from a network"),
        ("docker network disconnect -f <network> <container>", "Force-detach a container"),
        ("docker network rm <name>", "Remove a network"),
        ("docker network prune", "Remove all unused networks (asks first)"),
        ("docker network prune -f", "Remove all unused networks without asking"),
        ("docker network prune --filter until=<24h>", "Remove unused networks older than a time"),
    ]),
    ("COMPOSE", [
        # Inside the project folder (the folder with docker-compose.yml / compose.yaml) no -f is needed
        ("docker compose ls", "List running Compose projects"),
        ("docker compose ls -a", "List all Compose projects, including stopped ones"),
        ("docker compose up", "Create and start services, showing their logs (Ctrl+C stops them)"),
        ("docker compose up -d", "Create and start services in the background"),
        ("docker compose up --build", "Rebuild images, then start services (foreground)"),
        ("docker compose up -d --build", "Rebuild images, then start services in the background"),
        ("docker compose up -d --force-recreate", "Recreate containers even if nothing changed"),
        ("docker compose up -d --remove-orphans", "Also remove containers of services no longer in the file"),
        ("docker compose up -d <service>", "Start only one service (and what it depends on)"),
        ("docker compose up -d --no-deps <service>", "Start one service without its dependencies"),
        ("docker compose up -d --scale <service>=<n>", "Run n copies of a service"),
        ("docker compose build", "Build or rebuild service images"),
        ("docker compose build --no-cache", "Build without using the layer cache"),
        ("docker compose build <service>", "Build the image of one service"),
        ("docker compose pull", "Pull service images"),
        ("docker compose create", "Create containers without starting them"),
        ("docker compose start", "Start existing stopped services"),
        ("docker compose stop", "Stop services without removing them"),
        ("docker compose restart", "Restart all services"),
        ("docker compose restart <service>", "Restart one service"),
        ("docker compose pause", "Pause all services"),
        ("docker compose unpause", "Resume paused services"),
        ("docker compose kill", "Force-stop services (SIGKILL)"),
        ("docker compose down", "Stop and remove containers and networks"),
        ("docker compose down -v", "Also remove named volumes"),
        ("docker compose down --rmi all", "Also remove the images used by services"),
        ("docker compose down --remove-orphans", "Also remove containers of services not in the file"),
        ("docker compose rm -f", "Remove stopped service containers"),
        ("docker compose ps", "List the project's running containers"),
        ("docker compose ps -a", "List all of the project's containers, including stopped ones"),
        ("docker compose top", "Show running processes of each service"),
        ("docker compose images", "List the images used by the project"),
        ("docker compose logs", "View logs of all services"),
        ("docker compose logs -f", "Follow logs of all services live"),
        ("docker compose logs --tail 100", "View the last 100 log lines of all services"),
        ("docker compose logs -f <service>", "Follow logs of one service"),
        ("docker compose exec <service> sh", "Open a shell in a running service"),
        ("docker compose exec <service> <command>", "Run a command in a running service"),
        ("docker compose run --rm <service> <command>", "Run a one-off command in a new throw-away container"),
        ("docker compose cp <service>:<src> <dest>", "Copy files from a service container to the host"),
        ("docker compose config", "Show the final merged configuration"),
        ("docker compose config --services", "List the service names"),
        ("docker compose version", "Show the Compose version"),
        # Pointing Compose at a file, project name, env file or profile
        ("docker compose -f <file.yml> up -d", "Start services from a specific compose file"),
        ("docker compose -f <file.yml> down", "Stop and remove a project started from a specific file"),
        ("docker compose -f <a.yml> -f <b.yml> up -d", "Merge several compose files (later files override)"),
        ("docker compose -p <project> up -d", "Start under a custom project name"),
        ("docker compose -p <project> down", "Stop and remove a project by its name"),
        ("docker compose --env-file <file.env> up -d", "Use a specific .env file for variables"),
        ("docker compose --profile <name> up -d", "Also start services in a profile"),
    ]),
    ("SYSTEM", [
        ("docker system df", "Show disk usage by images, containers, volumes"),
        ("docker system df -v", "Verbose disk usage breakdown"),
        ("docker system prune", "Remove stopped containers, dangling images and unused networks (asks first)"),
        ("docker system prune -f", "Same, without asking"),
        ("docker system prune -a", "Also remove all unused images (not just dangling)"),
        ("docker system prune --volumes", "Also remove unused volumes"),
        ("docker system prune -a --volumes", "Full cleanup including unused images and volumes"),
        ("docker system prune --filter until=<24h>", "Only remove objects older than a time"),
        ("docker builder prune", "Remove the build cache"),
        ("docker builder prune -a", "Remove all build cache, not just unused"),
        ("docker builder prune -f", "Remove the build cache without asking"),
        ("docker info", "Show Docker system-wide information"),
        ("docker info --format '{{.ServerVersion}}'", "Show one field, here the server version"),
        ("docker version", "Show Docker client and server version"),
        ("docker events", "Stream real-time events from the daemon"),
        ("docker events --since <time>", "Show events since a time"),
        ("docker events --filter type=container", "Only container events"),
        ("docker events --filter event=die", "Only a specific event, here containers dying"),
        ("docker context ls", "List Docker contexts (local and remote engines)"),
        ("docker context use <name>", "Switch to another Docker context"),
        ("docker context create <name> --docker host=ssh://<user>@<host>", "Add a remote engine over SSH"),
        ("docker context inspect <name>", "Show a context's details"),
        ("docker help", "List all docker commands"),
        ("docker <command> --help", "Show help for any command, e.g. docker run --help"),
    ]),
]

COMMANDS_TITLE = "DOCKER COMMAND REFERENCE"


def commands_as_text():
    """Both sets as plain text (Copy all / Download)."""
    lines = [COMMANDS_TITLE, "=" * len(COMMANDS_TITLE), ""]
    for heading, sections in (("USED BY THIS APP", APP_COMMAND_SECTIONS), ("GENERAL REFERENCE", COMMAND_SECTIONS)):
        lines += ["#" * 3 + f" {heading} " + "#" * 3, ""]
        for title, commands in sections:
            lines += [f"── {title} " + "─" * max(3, 48 - len(title)), ""]
            for command, description in commands:
                lines += [f"  {command}", f"    {description}", ""]
    return "\n".join(lines).rstrip() + "\n"
