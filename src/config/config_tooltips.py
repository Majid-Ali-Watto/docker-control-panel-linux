"""
Tooltip text registry for the Docker GUI.
"""

SIDEBAR_TOOLTIPS = {
    "Docker": "Manage Docker service - start, stop, or restart",
    "Containers": "View and manage containers (run, stop, delete, logs, terminal)",
    "Images": "Browse, pull, and delete Docker images",
    "Volumes": "View and manage persistent Docker volumes",
    "Stats": "Monitor real-time container stats and disk usage",
}

CATEGORY_TOOLTIPS = {
    "Docker": {
        "Start": "Start the Docker service\n(systemctl start docker)",
        "Stop": "Stop the Docker service\n(systemctl stop docker)",
        "Restart": "Restart the Docker service\n(systemctl restart docker)",
        "Clean All": "Stop and permanently delete ALL\ncontainers, images, and volumes",
    },
    "Containers": {
        "All": "Show all containers - running and stopped",
        "Running": "Show only currently active (running) containers",
        "Stopped": "Show only exited or stopped containers",
        "Start All": "Start every stopped container",
        "Stop All": "Gracefully stop all running containers",
        "Restart All": "Restart all running containers",
        "Delete All": "Force-remove ALL containers (running and stopped)",
    },
    "Images": {
        "All": "Show all pulled Docker images",
        "Used": "Show images currently in use by at least one container",
        "Unused": "Show images not attached to any container (safe to delete)",
        "Pull": "Download a new image from Docker Hub\n(e.g. nginx:latest, ubuntu:22.04)",
        "Delete All": "Force-delete ALL local images",
    },
    "Volumes": {
        "Volumes": "Show all Docker volumes and which containers use them",
        "Prune (Unused)": "Remove all dangling (unused) volumes to free disk space",
        "Delete Used": "Remove volumes currently attached to containers",
        "Delete All": "Remove ALL volumes - used and unused",
    },
    "Stats": {
        "Container Stats": "Real-time CPU, memory, and network I/O\nfor all running containers",
        "Docker Disk Usage": "Detailed disk usage by images, containers,\nvolumes, and build cache",
        "Disk Storage Simple": "Summary table of total Docker disk usage",
    },
}

SIDEBAR_BOTTOM_TOOLTIPS = {
    "change_password": "Change or update the saved sudo password",
    "delete_password": "Remove the saved sudo password from disk",
    "relaunch_app": "Restart the application\n(useful after installing Docker or changing settings)",
}

ACTION_TOOLTIPS = {
    "start_container": "Start the selected container(s)",
    "stop_container": "Gracefully stop the selected container(s)",
    "delete_container": "Force-remove the selected container(s)",
    "container_terminal": "Open an interactive shell inside the selected container",
    "view_logs": "View stdout/stderr logs for the selected container",
    "delete_image": "Delete the selected image(s)",
    "delete_volume": "Permanently remove the selected volume(s)",
    "run_container": "Create and start a new container from the selected image",
    "stop_using_image": "Stop all containers that are currently using the selected image",
}
