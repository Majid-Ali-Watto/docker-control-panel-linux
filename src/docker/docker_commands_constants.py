"""
Docker Commands Constants
Centralized location for all Docker CLI commands used in the application.
"""

# System commands
DOCKER_DISK_STORAGE_SIMPLE = "docker system df"
DOCKER_DISK_USAGE_VERBOSE = "docker system df -v"
DOCKER_SYSTEM_PRUNE = "docker system prune -f"

# Container list commands
DOCKER_PS_RUNNING = "docker ps --format '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.Size}}'"
DOCKER_PS_ALL = "docker ps -a --format '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.Size}}'"
DOCKER_PS_STOPPED = "docker ps -a --filter 'status=exited' --format '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.Size}}'"
DOCKER_PS_PAUSED = "docker ps -a --filter 'status=paused' --format '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.Size}}'"
DOCKER_PS_IDS_ALL = "docker ps -aq"
DOCKER_PS_IDS_RUNNING = "docker ps -q"
DOCKER_PS_NAMES_ALL = "docker ps -a --format '{{.Names}}'"

# Container stats
DOCKER_STATS_NO_STREAM = "docker stats --no-stream --format '{{.ID}}\t{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}' $(docker ps -q)"

# Container actions
DOCKER_START_ALL = "docker start $(docker ps -aq)"
DOCKER_STOP_ALL = "docker stop $(docker ps -aq)"
DOCKER_RESTART_ALL = "docker restart $(docker ps -aq)"
DOCKER_RM_ALL = "docker rm -f $(docker ps -aq)"
DOCKER_STOP_ALL_SAFE = "docker stop $(docker ps -aq) 2>/dev/null || true"
DOCKER_RM_ALL_SAFE = "docker rm -f $(docker ps -aq) 2>/dev/null || true"
DOCKER_CONTAINER_START = "docker start {containers}"
DOCKER_CONTAINER_STOP = "docker stop {containers}"
DOCKER_CONTAINER_RESTART = "docker restart {containers}"
DOCKER_CONTAINER_RM = "docker rm -f {containers}"
DOCKER_CONTAINER_PAUSE = "docker pause {containers}"
DOCKER_CONTAINER_UNPAUSE = "docker unpause {containers}"
DOCKER_CONTAINER_RENAME = "docker rename {old_name} {new_name}"
DOCKER_CONTAINER_COMMIT = "docker commit {container} {image}"
DOCKER_CONTAINER_INSPECT = "docker inspect {container}"
DOCKER_CONTAINER_LOGS = "docker logs {timestamps_flag} --tail {lines} {container}"

# Image commands
DOCKER_IMAGES_ALL = "docker images --format '{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}'"
DOCKER_IMAGES_IDS_ALL = "docker images -aq"
DOCKER_RMI_ALL = "docker rmi -f $(docker images -aq)"
DOCKER_RMI_ALL_SAFE = "docker rmi -f $(docker images -aq) 2>/dev/null || true"
DOCKER_IMAGE_RM = "docker rmi -f {images}"
DOCKER_IMAGE_PRUNE = "docker image prune -f"
DOCKER_IMAGE_TAG = "docker tag {source} {target}"
DOCKER_IMAGE_SAVE = "docker save -o {output_file} {image}"
DOCKER_IMAGE_LOAD = "docker load -i {input_file}"
DOCKER_IMAGE_BUILD = "docker build {tag}{dockerfile}{build_args}{context}"
DOCKER_IMAGE_HISTORY = "docker history {image}"
DOCKER_IMAGE_INSPECT = "docker image inspect {image}"

# Volume commands
DOCKER_VOLUME_LS_IDS = "docker volume ls -q"
DOCKER_VOLUME_LS_DANGLING = "docker volume ls -qf dangling=true"
DOCKER_VOLUME_PRUNE = "docker volume prune -f"
DOCKER_VOLUME_RM_ALL = "docker volume rm $(docker volume ls -q)"
DOCKER_VOLUME_RM_ALL_SAFE = "docker volume rm $(docker volume ls -q) 2>/dev/null || true"
DOCKER_VOLUME_CREATE = "docker volume create {name}"
DOCKER_VOLUME_RM = "docker volume rm {volumes}"
DOCKER_VOLUME_INSPECT = "docker volume inspect {volume}"

# Network commands
DOCKER_NETWORK_LS = "docker network ls --format '{{.ID}}\t{{.Name}}\t{{.Driver}}\t{{.Scope}}'"
DOCKER_NETWORK_NAMES = "docker network ls --format '{{.Name}}'"
DOCKER_NETWORK_CREATE = "docker network create --driver {driver}{options} {name}"
DOCKER_NETWORK_RM = "docker network rm {networks}"
DOCKER_NETWORK_INSPECT = "docker network inspect {network}"
DOCKER_NETWORK_PRUNE = "docker network prune -f"
DOCKER_NETWORK_CONNECT = "docker network connect {network} {container}"
DOCKER_NETWORK_DISCONNECT = "docker network disconnect {network} {container}"

# Compose commands
DOCKER_COMPOSE_LS = "docker compose ls --format json"
DOCKER_COMPOSE_PS = "docker compose {files} ps --all --format json"
DOCKER_COMPOSE_UP = "docker compose {files} up -d"
DOCKER_COMPOSE_DOWN = "docker compose {files} down"
DOCKER_COMPOSE_RESTART = "docker compose {files} restart"
DOCKER_COMPOSE_LOGS = "docker compose {files} logs --tail {lines}"
DOCKER_COMPOSE_CONFIG = "docker compose {files} config"

# Inspect commands
DOCKER_INSPECT_IMAGE = "docker inspect --format='{{{{.Image}}}}' {container_id}"
DOCKER_INSPECT_MOUNTS = "docker inspect --format='{{{{json .Mounts}}}}' {container_name}"
DOCKER_INSPECT_ANCESTOR = "docker ps -a --filter ancestor={image_id} --format '{{{{.ID}}}}'"

# Pull command
DOCKER_PULL = "docker pull {image_name}"

# Run command
DOCKER_RUN_DETACHED = "docker run -d --restart {restart_policy}{name}{ports}{envs}{volumes}{network}{extra_args}{image}{command}"
