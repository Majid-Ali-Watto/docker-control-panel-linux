"""
Menu structure configuration for Docker GUI
Note: Function references will be resolved at import time in the main application
"""

# Buttons that switch which list is shown (they stay highlighted and can be reloaded in
# place). Every other button runs an action or opens a dialog.
VIEW_BUTTONS = {
    "Containers": {"All", "Running", "Stopped", "Paused"},
    "Images": {"All", "Used", "Unused"},
    "Volumes": {"Volumes", "Used", "Unused"},
    "Networks": {"All Networks"},
    "Compose": {"Projects"},
    "Stats": {"Container Stats", "Docker Disk Usage", "Disk Storage Simple"},
}


def get_menu_structure(
    start_docker, stop_docker, restart_docker, clean_all,
    show_all_containers, show_running_containers, show_stopped_containers, show_paused_containers,
    start_all_containers, stop_all_containers, restart_all_containers, delete_all_containers,
    show_images, show_used_images, show_unused_images, pull_image, search_hub, pull_status, build_image, build_status, load_image,
    prune_images, delete_all_images, show_volumes, show_used_volumes, show_unused_volumes, create_volume, prune_volumes,
    delete_used_volumes, delete_all_volumes, show_networks, create_network, prune_networks,
    show_compose_projects, compose_up_from_file, show_containers_with_stats, docker_disk_usage,
    docker_disk_storage_simple
):
    """
    Returns the menu structure with function references.
    This allows the functions to be defined in the main file and passed here.
    """
    return {
        "Docker": [
            ("Start", start_docker),
            ("Stop", stop_docker),
            ("Restart", restart_docker),
            ("Clean All", clean_all),
        ],
        "Containers": [
            ("All", show_all_containers),
            ("Running", show_running_containers),
            ("Stopped", show_stopped_containers),
            ("Paused", show_paused_containers),
            ("Start All", start_all_containers),
            ("Stop All", stop_all_containers),
            ("Restart All", restart_all_containers),
            ("Delete All", delete_all_containers),
        ],
        "Images": [
            ("All", show_images),
            ("Used", show_used_images),
            ("Unused", show_unused_images),
            ("Pull", pull_image),
            ("Search Hub", search_hub),
            ("Pull Status", pull_status),
            ("Build", build_image),
            ("Build Status", build_status),
            ("Load", load_image),
            ("Prune (Unused)", prune_images),
            ("Delete All", delete_all_images),
        ],
        "Volumes": [
            ("Volumes", show_volumes),
            ("Used", show_used_volumes),
            ("Unused", show_unused_volumes),
            ("Create", create_volume),
            ("Prune (Unused)", prune_volumes),
            ("Delete Used", delete_used_volumes),
            ("Delete All", delete_all_volumes),
        ],
        "Networks": [
            ("All Networks", show_networks),
            ("Create", create_network),
            ("Prune (Unused)", prune_networks),
        ],
        "Compose": [
            ("Projects", show_compose_projects),
            ("Up From File", compose_up_from_file),
        ],
        "Terminal": [],
        "Stats": [
            ("Container Stats", show_containers_with_stats),
            ("Docker Disk Usage", docker_disk_usage),
            ("Disk Storage Simple", docker_disk_storage_simple),
        ],
    }
