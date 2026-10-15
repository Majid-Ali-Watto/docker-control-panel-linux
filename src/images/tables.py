"""
Image table views.
"""

from src.docker.operations import show_table_command
from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password
from src.utils.utils import async_run, run_cmd
from src.docker.commands import (
    DOCKER_IMAGES_ALL,
    DOCKER_IMAGES_DANGLING,
    DOCKER_PS_IDS_ALL,
    DOCKER_INSPECT_IMAGE,
)


def show_images(show_table_callback, show_loading_callback):
    """Show all images"""
    if not check_docker_running(): return
    show_table_command(
        DOCKER_IMAGES_ALL,
        ["REPOSITORY", "TAG", "IMAGE ID", "SIZE", "CREATED"],
        sudo=True, sudo_password=get_sudo_password(),
        table_callback=show_table_callback,
        loading_callback=show_loading_callback,
        table_type='image',
        table_title="Images"
    )


def show_dangling_images(show_table_callback, show_loading_callback):
    """Show untagged (dangling) images, the layers `Prune` would remove"""
    if not check_docker_running(): return
    show_table_command(
        DOCKER_IMAGES_DANGLING,
        ["REPOSITORY", "TAG", "IMAGE ID", "SIZE", "CREATED"],
        sudo=True, sudo_password=get_sudo_password(),
        table_callback=show_table_callback,
        loading_callback=show_loading_callback,
        table_type='image',
        table_title="Dangling Images"
    )


def show_unused_images(show_table_callback, show_loading_callback, append=False):
    """Show unused images"""
    if not check_docker_running(): return

    def callback(result):
        all_image_rows = []
        for line in result.split('\n'):
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 4:
                    all_image_rows.append(parts)

        sudo_pw = get_sudo_password()
        container_ids = run_cmd(DOCKER_PS_IDS_ALL, sudo=True, sudo_password=sudo_pw).strip()
        used_image_ids = set()

        if container_ids:
            for container_id in container_ids.split('\n'):
                if container_id.strip():
                    image_sha = run_cmd(f"docker inspect --format='{{{{.Image}}}}' {container_id.strip()}", sudo=True, sudo_password=sudo_pw).strip()
                    if image_sha:
                        image_sha = image_sha.replace('sha256:', '')
                        used_image_ids.add(image_sha)
                        used_image_ids.add(image_sha[:12])

        unused_rows = [row for row in all_image_rows if row[2] not in used_image_ids]
        show_table_callback(["REPOSITORY", "TAG", "IMAGE ID", "SIZE", "CREATED"], unused_rows,
                          'image', "Unused Images", append)

    async_run(
        DOCKER_IMAGES_ALL,
        callback, sudo=True, sudo_password=get_sudo_password(), loading_callback=show_loading_callback
    )


def show_used_images(show_table_callback, show_loading_callback, append=False):
    """Show used images"""
    if not check_docker_running(): return

    def callback(result):
        all_image_rows = []
        for line in result.split('\n'):
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 4:
                    all_image_rows.append(parts)

        sudo_pw = get_sudo_password()
        container_ids = run_cmd(DOCKER_PS_IDS_ALL, sudo=True, sudo_password=sudo_pw).strip()
        used_image_ids = set()

        if container_ids:
            for container_id in container_ids.split('\n'):
                if container_id.strip():
                    image_sha = run_cmd(DOCKER_INSPECT_IMAGE.format(container_id=container_id.strip()), sudo=True, sudo_password=sudo_pw).strip()
                    if image_sha:
                        image_sha = image_sha.replace('sha256:', '')
                        used_image_ids.add(image_sha)
                        used_image_ids.add(image_sha[:12])

        used_rows = [row for row in all_image_rows if row[2] in used_image_ids]
        show_table_callback(["REPOSITORY", "TAG", "IMAGE ID", "SIZE", "CREATED"], used_rows,
                          'image', "Used Images", append)

    async_run(
        DOCKER_IMAGES_ALL,
        callback, sudo=True, sudo_password=get_sudo_password(), loading_callback=show_loading_callback
    )
