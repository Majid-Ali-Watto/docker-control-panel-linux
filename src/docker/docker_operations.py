"""
Docker Operations Module
Core Docker command execution and basic operations.
"""

from src.utils.utils import async_run


def run_docker_cmd(cmd, sudo=False, sudo_password=None, callback=None, loading_callback=None):
    """Run docker command with optional sudo"""
    async_run(cmd, callback, sudo=sudo, sudo_password=sudo_password, loading_callback=loading_callback)


def show_table_command(cmd, columns, sudo=False, sudo_password=None, table_callback=None, 
                      loading_callback=None, table_type=None, table_title=None, append=False):
    """Run docker command and show output in table"""
    def callback(result):
        rows = [line.split("\t") for line in result.splitlines() if line]
        if table_callback:
            table_callback(columns, rows, table_type, table_title, append)
    async_run(cmd, callback, sudo=sudo, sudo_password=sudo_password, loading_callback=loading_callback)
