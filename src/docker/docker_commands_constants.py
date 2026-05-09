"""
Docker Commands Constants
Centralized location for all Docker CLI commands used in the application.
"""

# System commands
DOCKER_DISK_STORAGE_SIMPLE = "docker system df"
DOCKER_DISK_USAGE_VERBOSE = "docker system df -v"

# Container list commands
DOCKER_PS_RUNNING = "docker ps --format '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.Size}}'"
DOCKER_PS_ALL = "docker ps -a --format '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.Size}}'"
DOCKER_PS_STOPPED = "docker ps -a --filter 'status=exited' --format '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.Size}}'"
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

# Image commands
DOCKER_IMAGES_ALL = "docker images --format '{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}'"
DOCKER_IMAGES_IDS_ALL = "docker images -aq"
DOCKER_RMI_ALL = "docker rmi -f $(docker images -aq)"
DOCKER_RMI_ALL_SAFE = "docker rmi -f $(docker images -aq) 2>/dev/null || true"

# Volume commands
DOCKER_VOLUME_LS_IDS = "docker volume ls -q"
DOCKER_VOLUME_LS_DANGLING = "docker volume ls -qf dangling=true"
DOCKER_VOLUME_PRUNE = "docker volume prune -f"
DOCKER_VOLUME_RM_ALL = "docker volume rm $(docker volume ls -q)"
DOCKER_VOLUME_RM_ALL_SAFE = "docker volume rm $(docker volume ls -q) 2>/dev/null || true"

# Inspect commands
DOCKER_INSPECT_IMAGE = "docker inspect --format='{{{{.Image}}}}' {container_id}"
DOCKER_INSPECT_MOUNTS = "docker inspect --format='{{{{json .Mounts}}}}' {container_name}"
DOCKER_INSPECT_ANCESTOR = "docker ps -a --filter ancestor={image_id} --format '{{{{.ID}}}}'"

# Pull command
DOCKER_PULL = "docker pull {image_name}"

# Run command
DOCKER_RUN_DETACHED = "docker run -d --restart unless-stopped {name}{image}"