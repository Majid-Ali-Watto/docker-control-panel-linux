"""
Docker commands reference shown in the Commands tab.
"""

commands_info = """
╔══════════════════════════════════════════════════╗
║         DOCKER COMMAND REFERENCE                 ║
╚══════════════════════════════════════════════════╝

── SERVICE ──────────────────────────────────────────

  systemctl start docker
    Start the Docker service

  systemctl stop docker
    Stop the Docker service

  systemctl restart docker
    Restart the Docker service

  systemctl status docker
    Check if Docker is running

── CONTAINERS ───────────────────────────────────────

  docker ps
    List running containers

  docker ps -a
    List all containers (including stopped)

  docker start <container>
    Start a stopped container

  docker stop <container>
    Stop a running container

  docker restart <container>
    Restart a container

  docker pause <container>
    Pause all processes in a container

  docker unpause <container>
    Resume a paused container

  docker rename <old> <new>
    Rename a container

  docker rm <container>
    Remove a stopped container

  docker rm -f <container>
    Force-remove a running container

  docker exec -it <container> bash
    Open an interactive shell in a container

  docker logs <container>
    View container logs

  docker logs -f <container>
    Follow (tail) container logs live

  docker inspect <container>
    Show detailed container metadata (JSON)

  docker commit <container> <image:tag>
    Create a new image from a container

  docker cp <container>:<src> <dest>
    Copy files from a container to the host

  docker cp <src> <container>:<dest>
    Copy files from the host to a container

  docker stats
    Show live container resource usage

  docker top <container>
    Show processes running inside a container

── IMAGES ───────────────────────────────────────────

  docker images
    List all local images

  docker pull <image>
    Download an image from Docker Hub

  docker pull <image>:<tag>
    Download a specific image tag

  docker search <term>
    Search Docker Hub for images

  docker push <image>
    Push a local image to a registry

  docker build -t <name:tag> <context>
    Build an image from a Dockerfile

  docker build -t <name:tag> -f <Dockerfile> .
    Build using a specific Dockerfile path

  docker build --build-arg KEY=val .
    Pass build-time variables to a Dockerfile

  docker load -i <archive.tar>
    Import an image from a tar archive

  docker save -o <archive.tar> <image>
    Export an image to a tar archive

  docker tag <source> <target>
    Create a new tag for an existing image

  docker rmi <image>
    Remove an image

  docker image prune
    Remove dangling (untagged) images

  docker image prune -a
    Remove all unused images

  docker image inspect <image>
    Show detailed image metadata (JSON)

  docker history <image>
    Show layer history of an image

── VOLUMES ──────────────────────────────────────────

  docker volume ls
    List all volumes

  docker volume create <name>
    Create a named volume

  docker volume inspect <name>
    Show volume details (JSON)

  docker volume rm <name>
    Remove a volume

  docker volume prune
    Remove all unused volumes

  docker system df -v
    Show verbose disk usage per volume

── NETWORKS ─────────────────────────────────────────

  docker network ls
    List all networks

  docker network create <name>
    Create a bridge network

  docker network create --driver overlay <name>
    Create an overlay network

  docker network inspect <name>
    Show network details (JSON)

  docker network connect <network> <container>
    Attach a container to a network

  docker network disconnect <network> <container>
    Detach a container from a network

  docker network rm <name>
    Remove a network

  docker network prune
    Remove all unused networks

── COMPOSE ──────────────────────────────────────────

  docker compose ls
    List active Compose projects

  docker compose up -d
    Start services in detached mode

  docker compose up -d --build
    Rebuild images then start services

  docker compose down
    Stop and remove containers + networks

  docker compose down -v
    Also remove named volumes

  docker compose restart
    Restart all services

  docker compose logs
    View logs from all services

  docker compose logs -f <service>
    Follow logs for a specific service

  docker compose ps
    Show status of Compose services

  docker compose config
    Show the final merged Compose config

── SYSTEM ───────────────────────────────────────────

  docker system df
    Show disk usage by images, containers, volumes

  docker system df -v
    Verbose disk usage breakdown

  docker system prune
    Remove all stopped containers, dangling
    images, unused networks

  docker system prune -a
    Also remove unused images (not just dangling)

  docker system prune -a --volumes
    Full cleanup including unused volumes

  docker info
    Show Docker system-wide information

  docker version
    Show Docker client and server version
"""
