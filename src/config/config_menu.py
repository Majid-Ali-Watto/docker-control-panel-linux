"""
Menu structure configuration for Docker GUI
Note: Function references will be resolved at import time in the main application
"""

def get_menu_structure(
    start_docker, stop_docker, restart_docker, clean_all,
    show_all_containers, show_running_containers, show_stopped_containers,
    start_all_containers, stop_all_containers, restart_all_containers, delete_all_containers,
    show_images, show_used_images, show_unused_images, pull_image, delete_all_images,
    show_volumes, prune_volumes, delete_used_volumes, delete_all_volumes,
    show_containers_with_stats, docker_disk_usage, docker_disk_storage_simple
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
            ("Delete All", delete_all_images),
        ],
        "Volumes": [
            ("Volumes", show_volumes),
            ("Prune (Unused)", prune_volumes),
            ("Delete Used", delete_used_volumes),
            ("Delete All", delete_all_volumes),
        ],
        "Stats": [
            ("Container Stats", show_containers_with_stats),
            ("Docker Disk Usage", docker_disk_usage),
            ("Disk Storage Simple", docker_disk_storage_simple),
        ],
    }
