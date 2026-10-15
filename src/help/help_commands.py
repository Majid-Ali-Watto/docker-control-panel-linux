"""
Docker commands reference shown in the Commands tab.

COMMAND_SECTIONS is the single source: the Commands tab renders it (click a command to copy it)
and `commands_as_text()` flattens it for "Copy all" / "Download".
"""

COMMAND_SECTIONS = [
    ("SERVICE", [
        ("systemctl start docker", "Start the Docker service"),
        ("systemctl stop docker", "Stop the Docker service"),
        ("systemctl restart docker", "Restart the Docker service"),
        ("systemctl status docker", "Check if Docker is running"),
        ("systemctl enable docker", "Start Docker automatically at boot"),
        ("systemctl disable docker", "Do not start Docker at boot"),
        ("journalctl -u docker -f", "Follow the Docker daemon log"),
    ]),
    ("CONTAINERS", [
        ("docker ps", "List running containers"),
        ("docker ps -a", "List all containers (including stopped)"),
        ("docker ps -aq", "List only the IDs of all containers"),
        ("docker ps -a --filter status=exited", "List stopped containers"),
        ("docker ps -a --filter status=paused", "List paused containers"),
        ("docker run -d --name <name> -p <host>:<container> <image>", "Create and start a container in the background"),
        ("docker run -it --rm <image> sh", "Run a throw-away interactive container"),
        ("docker run -d --restart always -e KEY=val -v <host>:<container> <image>",
         "Run with restart policy, environment variable and volume mount"),
        ("docker create --name <name> <image>", "Create a container without starting it"),
        ("docker start <container>", "Start a stopped container"),
        ("docker stop <container>", "Stop a running container"),
        ("docker restart <container>", "Restart a container"),
        ("docker kill <container>", "Send SIGKILL to a running container"),
        ("docker pause <container>", "Pause all processes in a container"),
        ("docker unpause <container>", "Resume a paused container"),
        ("docker rename <old> <new>", "Rename a container"),
        ("docker rm <container>", "Remove a stopped container"),
        ("docker rm -f <container>", "Force-remove a running container"),
        ("docker start $(docker ps -aq)", "Start every container"),
        ("docker stop $(docker ps -aq)", "Stop every container"),
        ("docker restart $(docker ps -aq)", "Restart every container"),
        ("docker rm -f $(docker ps -aq)", "Force-remove every container"),
        ("docker container prune -f", "Remove all stopped containers"),
        ("docker exec -it <container> bash", "Open an interactive shell in a container"),
        ("docker exec <container> ls -la <path>", "List files inside a container"),
        ("docker logs <container>", "View container logs"),
        ("docker logs -f --tail 100 <container>", "Follow the last 100 log lines live"),
        ("docker logs -t <container>", "View logs with timestamps"),
        ("docker inspect <container>", "Show detailed container metadata (JSON)"),
        ("docker diff <container>", "Show files changed in a container's filesystem"),
        ("docker port <container>", "Show a container's published ports"),
        ("docker commit <container> <image:tag>", "Create a new image from a container"),
        ("docker export -o <file.tar> <container>", "Export a container's filesystem to a tar archive"),
        ("docker cp <container>:<src> <dest>", "Copy files from a container to the host"),
        ("docker cp <src> <container>:<dest>", "Copy files from the host to a container"),
        ("docker update --restart unless-stopped <container>", "Change a container's restart policy"),
        ("docker wait <container>", "Block until a container stops, then print its exit code"),
        ("docker stats", "Show live container resource usage"),
        ("docker stats --no-stream", "Show a one-time snapshot of resource usage"),
        ("docker top <container>", "Show processes running inside a container"),
    ]),
    ("IMAGES", [
        ("docker images", "List all local images"),
        ("docker images -aq", "List only the IDs of all images"),
        ("docker pull <image>", "Download an image from Docker Hub"),
        ("docker pull <image>:<tag>", "Download a specific image tag"),
        ("docker search <term>", "Search Docker Hub for images"),
        ("docker login", "Log in to a registry"),
        ("docker logout", "Log out from a registry"),
        ("docker push <image>", "Push a local image to a registry"),
        ("docker build -t <name:tag> <context>", "Build an image from a Dockerfile"),
        ("docker build -t <name:tag> -f <Dockerfile> .", "Build using a specific Dockerfile path"),
        ("docker build --build-arg KEY=val .", "Pass build-time variables to a Dockerfile"),
        ("docker build --no-cache -t <name:tag> .", "Build without using the layer cache"),
        ("docker load -i <archive.tar>", "Import an image from a tar archive"),
        ("docker save -o <archive.tar> <image>", "Export an image to a tar archive"),
        ("docker import <file.tar> <image:tag>", "Create an image from an exported filesystem"),
        ("docker tag <source> <target>", "Create a new tag for an existing image"),
        ("docker rmi <image>", "Remove an image"),
        ("docker rmi -f <image>", "Force-remove an image"),
        ("docker rmi -f $(docker images -aq)", "Force-remove every image"),
        ("docker image prune -f", "Remove dangling (untagged) images"),
        ("docker image prune -a", "Remove all unused images"),
        ("docker image inspect <image>", "Show detailed image metadata (JSON)"),
        ("docker history <image>", "Show layer history of an image"),
        ("docker ps -a --filter ancestor=<image>", "List containers created from an image"),
    ]),
    ("VOLUMES", [
        ("docker volume ls", "List all volumes"),
        ("docker volume ls -q", "List only volume names"),
        ("docker volume ls -qf dangling=true", "List volumes not used by any container"),
        ("docker volume create <name>", "Create a named volume"),
        ("docker volume inspect <name>", "Show volume details (JSON)"),
        ("docker volume rm <name>", "Remove a volume"),
        ("docker volume rm $(docker volume ls -q)", "Remove every volume"),
        ("docker volume prune -f", "Remove all unused volumes"),
        ("docker system df -v", "Show verbose disk usage per volume"),
    ]),
    ("NETWORKS", [
        ("docker network ls", "List all networks"),
        ("docker network create <name>", "Create a bridge network"),
        ("docker network create --driver overlay <name>", "Create an overlay network"),
        ("docker network create --subnet <cidr> <name>", "Create a network with a custom subnet"),
        ("docker network inspect <name>", "Show network details (JSON)"),
        ("docker network connect <network> <container>", "Attach a container to a network"),
        ("docker network disconnect <network> <container>", "Detach a container from a network"),
        ("docker network rm <name>", "Remove a network"),
        ("docker network prune -f", "Remove all unused networks"),
    ]),
    ("COMPOSE", [
        ("docker compose ls", "List active Compose projects"),
        ("docker compose -f <file.yml> up -d", "Start services in detached mode"),
        ("docker compose -f <file.yml> up -d --build", "Rebuild images then start services"),
        ("docker compose -f <file.yml> build", "Build or rebuild service images"),
        ("docker compose -f <file.yml> pull", "Pull service images"),
        ("docker compose -f <file.yml> stop", "Stop services without removing them"),
        ("docker compose -f <file.yml> down", "Stop and remove containers + networks"),
        ("docker compose -f <file.yml> down -v", "Also remove named volumes"),
        ("docker compose -f <file.yml> restart", "Restart all services"),
        ("docker compose -f <file.yml> logs --tail 200", "View the last 200 log lines of all services"),
        ("docker compose -f <file.yml> logs -f <service>", "Follow logs for a specific service"),
        ("docker compose -f <file.yml> ps --all", "Show status of Compose services"),
        ("docker compose -f <file.yml> exec <service> sh", "Open a shell in a running service"),
        ("docker compose -f <file.yml> config", "Show the final merged Compose config"),
    ]),
    ("SYSTEM", [
        ("docker system df", "Show disk usage by images, containers, volumes"),
        ("docker system df -v", "Verbose disk usage breakdown"),
        ("docker system prune -f", "Remove stopped containers, dangling images and unused networks"),
        ("docker system prune -a", "Also remove unused images (not just dangling)"),
        ("docker system prune -a --volumes", "Full cleanup including unused volumes"),
        ("docker builder prune", "Remove the build cache"),
        ("docker events", "Stream real-time events from the daemon"),
        ("docker info", "Show Docker system-wide information"),
        ("docker version", "Show Docker client and server version"),
        ("docker context ls", "List Docker contexts (local and remote engines)"),
    ]),
]

COMMANDS_TITLE = "DOCKER COMMAND REFERENCE"


def commands_as_text():
    """The whole reference as plain text (Copy all / Download)."""
    lines = [COMMANDS_TITLE, "=" * len(COMMANDS_TITLE), ""]
    for title, commands in COMMAND_SECTIONS:
        lines += [f"── {title} " + "─" * max(3, 48 - len(title)), ""]
        for command, description in commands:
            lines += [f"  {command}", f"    {description}", ""]
    return "\n".join(lines).rstrip() + "\n"


commands_info = commands_as_text()
