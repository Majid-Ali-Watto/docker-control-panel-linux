"""
Image bulk actions (delete all, prune).
"""

from src.docker.actions import check_docker_running, confirm_and_run
from src.docker.commands import DOCKER_RMI_ALL, DOCKER_IMAGE_PRUNE


def delete_all_images(show_text_output_callback, parent=None, show_loading_callback=None):
    if not check_docker_running(): return
    confirm_and_run("Delete ALL images?", DOCKER_RMI_ALL,
                   show_text_output_callback, sudo=True, parent=parent,
                   show_loading_callback=show_loading_callback)


def prune_images(show_text_output_callback, parent=None, show_loading_callback=None):
    if not check_docker_running(): return
    confirm_and_run("Delete dangling/unused image layers?", DOCKER_IMAGE_PRUNE,
                   show_text_output_callback, sudo=True, parent=parent,
                   show_loading_callback=show_loading_callback)
