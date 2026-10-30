"""
System actions: engine info, builders and build cache.
"""

from src.docker.actions import check_docker_running, confirm_and_run
from src.config.config_manager import get_sudo_password
from src.utils.utils import async_run
from src.docker.commands import DOCKER_BUILDER_PRUNE, DOCKER_BUILDX_LS, DOCKER_INFO, DOCKER_VERSION


def show_system_info(show_text_output_callback, show_loading_callback=None):
    """Client / server versions followed by the daemon's `docker info`."""
    password = get_sudo_password()

    def with_version(version):
        def with_info(info):
            show_text_output_callback(f"DOCKER VERSION\n\n{version}\n\n\nDOCKER INFO\n\n{info}")
        async_run(DOCKER_INFO, with_info, sudo=True, sudo_password=password,
                  loading_callback=show_loading_callback)

    async_run(DOCKER_VERSION, with_version, sudo=True, sudo_password=password)


def show_builders(show_text_output_callback, show_loading_callback=None):
    """Buildx builders and the platforms they can build for."""
    if not check_docker_running(): return

    def done(result):
        if "unknown command" in result.lower():
            result = ("The buildx plugin is not installed, so there are no builders to list.\n\n"
                      "Install it with:  sudo apt install docker-buildx")
        show_text_output_callback(f"Builders\n\n{result}")

    async_run(DOCKER_BUILDX_LS, done, sudo=True, sudo_password=get_sudo_password(),
              loading_callback=show_loading_callback)


def prune_build_cache(show_text_output_callback, parent=None, show_loading_callback=None):
    """Remove the build cache that is not used by any build."""
    if not check_docker_running(): return
    confirm_and_run("Remove the unused build cache?\n\nThe next builds start from scratch.",
                    DOCKER_BUILDER_PRUNE, show_text_output_callback, sudo=True, parent=parent,
                    show_loading_callback=show_loading_callback)
