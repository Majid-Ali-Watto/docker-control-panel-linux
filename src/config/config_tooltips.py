"""
Tooltip text registry for the Docker GUI.
"""

SIDEBAR_TOOLTIPS = {
    "Docker": "Manage Docker service - start, stop, or restart",
    "Containers": "View and manage containers (run, stop, delete, logs, terminal)",
    "Images": "Browse, pull, and delete Docker images",
    "Volumes": "View and manage persistent Docker volumes",
    "Networks": "Inspect and manage Docker bridge and user-defined networks",
    "Compose": "Manage Docker Compose projects and their services",
    "Stats": "Monitor real-time container stats and disk usage",
    "Terminal": "General-purpose shell — run any command, navigate directories",
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
        "Paused": "Show containers whose processes are currently frozen with docker pause",
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
        "Pull Status": "Reopen the latest image pull progress or final result window",
        "Search Hub": "Search Docker Hub for public images by keyword",
        "Build": "Build a Docker image from a folder containing a Dockerfile",
        "Build Status": "Reopen the latest image build progress or final result window",
        "Load": "Import an image archive created with docker save",
        "Prune (Unused)": "Delete dangling image layers not referenced by tagged images",
        "Delete All": "Force-delete ALL local images",
    },
    "Volumes": {
        "Volumes": "Show all Docker volumes and which containers use them",
        "Used": "Show only volumes currently attached to one or more containers",
        "Unused": "Show only volumes not attached to any container",
        "Create": "Create a new named Docker volume",
        "Prune (Unused)": "Remove all dangling (unused) volumes to free disk space",
        "Delete Used": "Remove volumes currently attached to containers",
        "Delete All": "Remove ALL volumes - used and unused",
    },
    "Networks": {
        "All Networks": "Show all Docker networks with driver and scope details",
        "Create": "Create a new bridge, overlay, or host-style Docker network",
        "Prune (Unused)": "Delete unused Docker networks",
    },
    "Compose": {
        "Projects": "Show Docker Compose projects detected by Docker",
        "Up From File": "Choose a compose file and start the project in detached mode",
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
    "restart_container": "Restart the selected container(s)",
    "pause_container": "Pause all processes in the selected container(s)",
    "unpause_container": "Resume paused container(s)",
    "delete_container": "Force-remove the selected container(s)",
    "rename_container": "Rename the selected container",
    "container_terminal": "Open an interactive shell inside the selected container",
    "view_logs": "View stdout/stderr logs for the selected container",
    "inspect_container": "Show full docker inspect output for the selected container",
    "commit_container": "Create a new image snapshot from the selected container",
    "browse_files": "Browse the container filesystem, download or upload files",
    "delete_image": "Delete the selected image(s)",
    "push_image": "Push the selected image to a registry (Docker Hub or private)",
    "tag_image": "Create a new tag for the selected image",
    "save_image": "Export the selected image to a tar archive",
    "inspect_image": "Show detailed metadata for the selected image",
    "history_image": "Show the build/layer history for the selected image",
    "delete_volume": "Permanently remove the selected volume(s)",
    "inspect_volume": "Show detailed metadata for the selected volume",
    "run_container": "Create and start a new container from the selected image",
    "stop_using_image": "Stop all containers that are currently using the selected image",
    "delete_network": "Delete the selected network(s)",
    "inspect_network": "Show detailed metadata for the selected network",
    "connect_network": "Attach a container to the selected network",
    "disconnect_network": "Detach a container from the selected network",
    "compose_up": "Start or recreate services for the selected compose project",
    "compose_down": "Stop and remove resources for the selected compose project",
    "compose_restart": "Restart services for the selected compose project",
    "compose_logs": "Show recent logs for the selected compose project",
    "compose_services": "List services/containers for the selected compose project",
    "compose_inspect": "Show the rendered config for the selected compose project",
}
