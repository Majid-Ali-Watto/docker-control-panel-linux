"""
tests/test_buttons.py

Tests every sidebar button in the Docker GUI.
Each test verifies the correct Docker command is issued when a button action
is triggered, without spawning real Docker processes or a display.

Run with:
    python -m pytest tests/
    python -m unittest discover tests/
"""

import sys
import unittest
from unittest.mock import patch, MagicMock

# Stub ttkbootstrap before any app module is imported
sys.modules.setdefault('ttkbootstrap', MagicMock())

import tkinter as tk
from tkinter import ttk

from src.docker.commands import (
    DOCKER_PS_RUNNING, DOCKER_PS_ALL, DOCKER_PS_STOPPED, DOCKER_PS_PAUSED,
    DOCKER_STATS_NO_STREAM, DOCKER_IMAGES_ALL, DOCKER_PS_IDS_ALL,
    DOCKER_PS_IDS_RUNNING, DOCKER_PS_NAMES_ALL,
    DOCKER_START_ALL, DOCKER_STOP_ALL, DOCKER_RESTART_ALL, DOCKER_RM_ALL,
    DOCKER_RMI_ALL, DOCKER_IMAGE_PRUNE,
    DOCKER_VOLUME_PRUNE, DOCKER_VOLUME_RM_ALL, DOCKER_DISK_STORAGE_SIMPLE,
    DOCKER_DISK_USAGE_VERBOSE,
    DOCKER_NETWORK_LS, DOCKER_NETWORK_PRUNE, DOCKER_COMPOSE_LS,
    DOCKER_STOP_ALL_SAFE, DOCKER_RM_ALL_SAFE, DOCKER_RMI_ALL_SAFE, DOCKER_VOLUME_RM_ALL_SAFE,
    DOCKER_VOLUME_LS_IDS, DOCKER_VOLUME_LS_DANGLING,
    # Container actions
    DOCKER_CONTAINER_START, DOCKER_CONTAINER_STOP, DOCKER_CONTAINER_RESTART,
    DOCKER_CONTAINER_RM, DOCKER_CONTAINER_PAUSE, DOCKER_CONTAINER_UNPAUSE,
    DOCKER_CONTAINER_RENAME, DOCKER_CONTAINER_COMMIT, DOCKER_CONTAINER_INSPECT,
    DOCKER_CONTAINER_LOGS, DOCKER_EXEC_LS, DOCKER_CP_FROM, DOCKER_CP_TO,
    # Image actions
    DOCKER_IMAGES_IDS_ALL,
    DOCKER_IMAGE_RM, DOCKER_IMAGE_TAG, DOCKER_IMAGE_SAVE, DOCKER_IMAGE_LOAD,
    DOCKER_IMAGE_BUILD, DOCKER_IMAGE_HISTORY, DOCKER_IMAGE_INSPECT, DOCKER_IMAGE_PUSH,
    # Volume actions
    DOCKER_VOLUME_CREATE, DOCKER_VOLUME_RM, DOCKER_VOLUME_INSPECT,
    # Network actions
    DOCKER_NETWORK_NAMES, DOCKER_NETWORK_CREATE, DOCKER_NETWORK_RM,
    DOCKER_NETWORK_INSPECT, DOCKER_NETWORK_CONNECT, DOCKER_NETWORK_DISCONNECT,
    # Compose actions
    DOCKER_COMPOSE_PS, DOCKER_COMPOSE_UP, DOCKER_COMPOSE_DOWN,
    DOCKER_COMPOSE_RESTART, DOCKER_COMPOSE_LOGS, DOCKER_COMPOSE_CONFIG,
    # Inspect / run
    DOCKER_INSPECT_IMAGE, DOCKER_INSPECT_MOUNTS, DOCKER_INSPECT_ANCESTOR,
    DOCKER_PULL, DOCKER_SEARCH, DOCKER_RUN_DETACHED,
    DOCKER_SYSTEM_PRUNE,
)

FAKE_PW = 'testpw'

# Fake Treeview rows: (serial_no, *data_columns) matching how DisplayManager stores them
_F_CONTAINER = (1, 'c1a2b3c4d5e6', 'mycontainer', 'nginx:latest', 'Up 5h', '80/tcp', '50MB')
_F_IMAGE     = (1, 'nginx', 'latest', 'img1234567890', '100MB')
_F_VOLUME    = (1, 'myvol', '0', '50MB', '(unused)')
_F_NETWORK   = (1, 'net1234567890', 'mynetwork', 'bridge', 'local')
_F_COMPOSE   = (1, 'myapp', 'running', '/app/docker-compose.yml')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sync_thread(fn):
    """Drop-in for startThreadForTask: runs fn synchronously."""
    fn()


def _table_cb():
    """Return (callback, calls-list). Callback stores positional args."""
    calls = []
    def cb(columns, rows, *_):
        calls.append({'columns': columns, 'rows': rows})
    return cb, calls


# ---------------------------------------------------------------------------
# Base test class
# ---------------------------------------------------------------------------

class _Base(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.output = []
        self.show_output = lambda t: self.output.append(t)
        self.show_loading = MagicMock()

    def tearDown(self):
        self.root.destroy()


# ===========================================================================
# 1. Docker service buttons  (Docker → Start / Stop / Restart)
# ===========================================================================

class TestDockerServiceButtons(_Base):

    @patch('src.docker.actions.startThreadForTask', side_effect=_sync_thread)
    @patch('src.docker.actions.update_docker_status')
    @patch('src.docker.actions.get_sudo_password', return_value=FAKE_PW)
    @patch('src.docker.actions.run_cmd', return_value='active')
    def test_start_docker(self, mock_run, *_):
        from src.docker.actions import start_docker_service
        with patch('time.sleep'):
            start_docker_service(self.root, tk.StringVar(), self.show_loading, self.show_output)
        mock_run.assert_any_call(
            'systemctl start docker.socket docker.service',
            sudo=True, sudo_password=FAKE_PW,
        )
        self.assertTrue(any('Start Docker' in t for t in self.output))

    @patch('src.docker.actions.startThreadForTask', side_effect=_sync_thread)
    @patch('src.docker.actions.update_docker_status')
    @patch('src.docker.actions.get_sudo_password', return_value=FAKE_PW)
    @patch('src.docker.actions.run_cmd', return_value='inactive')
    def test_stop_docker(self, mock_run, *_):
        from src.docker.actions import stop_docker_service
        with patch('time.sleep'):
            stop_docker_service(self.root, tk.StringVar(), self.show_loading, self.show_output)
        mock_run.assert_any_call(
            'systemctl stop docker.socket docker.service',
            sudo=True, sudo_password=FAKE_PW,
        )

    @patch('src.docker.actions.startThreadForTask', side_effect=_sync_thread)
    @patch('src.docker.actions.update_docker_status')
    @patch('src.docker.actions.get_sudo_password', return_value=FAKE_PW)
    @patch('src.docker.actions.run_cmd', return_value='active')
    def test_restart_docker(self, mock_run, *_):
        from src.docker.actions import restart_docker_service
        with patch('time.sleep'):
            restart_docker_service(self.root, tk.StringVar(), self.show_loading, self.show_output)
        mock_run.assert_any_call(
            'systemctl restart docker.socket docker.service',
            sudo=True, sudo_password=FAKE_PW,
        )


# ===========================================================================
# 2. Container table buttons  (Containers → All / Running / Stopped / Paused)
# ===========================================================================

_FAKE_CONTAINER_ROW = 'abc123\tnginx\tnginx:latest\tUp 5h\t80/tcp\t50MB'


class TestContainerTableButtons(_Base):

    def _patches(self, run_return=_FAKE_CONTAINER_ROW):
        return [
            patch('src.containers.tables.check_docker_running', return_value=True),
            patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread),
            patch('src.containers.tables.get_sudo_password', return_value=FAKE_PW),
            patch('src.utils.utils.run_cmd', return_value=run_return),
        ]

    def _run(self, fn, run_return=_FAKE_CONTAINER_ROW):
        cb, calls = _table_cb()
        patches = self._patches(run_return)
        for p in patches:
            p.start()
        try:
            fn(cb, self.show_loading)
        finally:
            for p in patches:
                p.stop()
        return calls

    def test_show_all_containers(self):
        from src.containers.tables import show_all_containers
        calls = self._run(show_all_containers)
        self.assertTrue(calls)
        self.assertIn('CONTAINER ID', calls[0]['columns'])
        self.assertEqual(len(calls[0]['rows']), 1)
        self.assertEqual(calls[0]['rows'][0][0], 'abc123')

    def test_show_running_containers(self):
        from src.containers.tables import show_running_containers
        calls = self._run(lambda cb, ld: show_running_containers(cb, ld))
        self.assertTrue(calls)
        self.assertIn('CONTAINER ID', calls[0]['columns'])

    def test_show_stopped_containers(self):
        from src.containers.tables import show_stopped_containers
        calls = self._run(lambda cb, ld: show_stopped_containers(cb, ld))
        self.assertTrue(calls)
        self.assertIn('STATUS', calls[0]['columns'])

    def test_show_paused_containers(self):
        from src.containers.tables import show_paused_containers
        calls = self._run(lambda cb, ld: show_paused_containers(cb, ld))
        self.assertTrue(calls)
        self.assertIn('CONTAINER ID', calls[0]['columns'])

    def test_show_all_containers_empty(self):
        from src.containers.tables import show_all_containers
        calls = self._run(show_all_containers, run_return='')
        self.assertTrue(calls)
        self.assertEqual(calls[0]['rows'], [])


# ===========================================================================
# 3. Container action buttons  (Start All / Stop All / Restart All / Delete All)
# ===========================================================================

class TestContainerActionButtons(_Base):

    @patch('src.containers.actions.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.containers.actions.get_sudo_password', return_value=FAKE_PW)
    @patch('src.utils.utils.run_cmd', return_value='started')
    def test_start_all_containers(self, mock_run, *_):
        from src.containers.actions import start_all_containers
        start_all_containers(self.show_output, self.show_loading)
        mock_run.assert_called_once_with(DOCKER_START_ALL, True, FAKE_PW)

    @patch('src.containers.actions.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.containers.actions.get_sudo_password', return_value=FAKE_PW)
    @patch('src.utils.utils.run_cmd', return_value='stopped')
    def test_stop_all_containers(self, mock_run, *_):
        from src.containers.actions import stop_all_containers
        stop_all_containers(self.show_output, self.show_loading)
        mock_run.assert_called_once_with(DOCKER_STOP_ALL, True, FAKE_PW)

    @patch('src.containers.actions.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.containers.actions.get_sudo_password', return_value=FAKE_PW)
    @patch('src.utils.utils.run_cmd', return_value='restarted')
    def test_restart_all_containers(self, mock_run, *_):
        from src.containers.actions import restart_all_containers
        restart_all_containers(self.show_output, self.show_loading)
        mock_run.assert_called_once_with(DOCKER_RESTART_ALL, True, FAKE_PW)

    @patch('src.containers.actions.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.docker.actions.get_sudo_password', return_value=FAKE_PW)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=True)
    @patch('src.utils.utils.run_cmd', return_value='deleted')
    def test_delete_all_containers_confirmed(self, mock_run, *_):
        from src.containers.actions import delete_all_containers
        delete_all_containers(self.show_output, parent=self.root, show_loading_callback=self.show_loading)
        mock_run.assert_called_once_with(DOCKER_RM_ALL, True, FAKE_PW)

    @patch('src.containers.actions.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=False)
    @patch('src.utils.utils.run_cmd', return_value='')
    def test_delete_all_containers_cancelled(self, mock_run, *_):
        from src.containers.actions import delete_all_containers
        delete_all_containers(self.show_output, parent=self.root)
        mock_run.assert_not_called()


# ===========================================================================
# 4. Image buttons  (All / Unused / Prune / Delete All)
# ===========================================================================

_FAKE_IMAGE_ROWS = 'nginx\tlatest\tabc123\t100MB\nubuntu\t22.04\tdef456\t200MB'


class TestImageButtons(_Base):

    @patch('src.images.tables.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.images.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.utils.utils.run_cmd', return_value=_FAKE_IMAGE_ROWS)
    def test_show_all_images(self, *_):
        cb, calls = _table_cb()
        from src.images.tables import show_images
        show_images(cb, self.show_loading)
        self.assertTrue(calls)
        self.assertIn('REPOSITORY', calls[0]['columns'])
        self.assertEqual(len(calls[0]['rows']), 2)
        self.assertEqual(calls[0]['rows'][0][0], 'nginx')

    @patch('src.images.tables.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.images.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.utils.utils.run_cmd', return_value=_FAKE_IMAGE_ROWS)
    @patch('src.images.tables.run_cmd', return_value='')  # no running containers
    def test_show_unused_images_all_unused_when_no_containers(self, *_):
        cb, calls = _table_cb()
        from src.images.tables import show_unused_images
        show_unused_images(cb, self.show_loading)
        self.assertTrue(calls)
        self.assertEqual(len(calls[0]['rows']), 2)

    @patch('src.images.actions.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.docker.actions.get_sudo_password', return_value=FAKE_PW)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=True)
    @patch('src.utils.utils.run_cmd', return_value='pruned')
    def test_prune_images_confirmed(self, mock_run, *_):
        from src.images.actions import prune_images
        prune_images(self.show_output, parent=self.root, show_loading_callback=self.show_loading)
        mock_run.assert_called_once_with(DOCKER_IMAGE_PRUNE, True, FAKE_PW)

    @patch('src.images.actions.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=False)
    @patch('src.utils.utils.run_cmd', return_value='')
    def test_prune_images_cancelled(self, mock_run, *_):
        from src.images.actions import prune_images
        prune_images(self.show_output, parent=self.root)
        mock_run.assert_not_called()

    @patch('src.images.actions.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.docker.actions.get_sudo_password', return_value=FAKE_PW)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=True)
    @patch('src.utils.utils.run_cmd', return_value='deleted')
    def test_delete_all_images_confirmed(self, mock_run, *_):
        from src.images.actions import delete_all_images
        delete_all_images(self.show_output, parent=self.root, show_loading_callback=self.show_loading)
        mock_run.assert_called_once_with(DOCKER_RMI_ALL, True, FAKE_PW)

    @patch('src.images.actions.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=False)
    @patch('src.utils.utils.run_cmd', return_value='')
    def test_delete_all_images_cancelled(self, mock_run, *_):
        from src.images.actions import delete_all_images
        delete_all_images(self.show_output, parent=self.root)
        mock_run.assert_not_called()


# ===========================================================================
# 5. Volume buttons  (Volumes / Used / Unused / Prune / Delete All)
# ===========================================================================

_FAKE_DF_VOLUMES = (
    'Local Volumes space usage:\n'
    'VOLUME NAME   LINKS   SIZE\n'
    'vol1          1       50MB\n'
    'vol2          0       20MB\n'
)


class TestVolumeButtons(_Base):

    def _async_with_df(self, *args, **_):
        args[1](_FAKE_DF_VOLUMES)

    @patch('src.volumes.tables.check_docker_running', return_value=True)
    @patch('src.volumes.tables.run_cmd', return_value='')
    def test_show_volumes(self, *_):
        cb, calls = _table_cb()
        from src.volumes.tables import show_volumes
        with patch('src.volumes.tables.async_run', side_effect=self._async_with_df):
            show_volumes(cb, self.show_loading)
        self.assertTrue(calls)
        self.assertIn('VOLUME NAME', calls[0]['columns'])

    @patch('src.volumes.tables.check_docker_running', return_value=True)
    @patch('src.volumes.tables.run_cmd', return_value='')
    def test_show_unused_volumes(self, *_):
        cb, calls = _table_cb()
        from src.volumes.tables import show_unused_volumes
        with patch('src.volumes.tables.async_run', side_effect=self._async_with_df):
            show_unused_volumes(cb, self.show_loading)
        self.assertTrue(calls)
        unused = [r for r in calls[0]['rows'] if r[3] == '(unused)']
        self.assertEqual(len(unused), len(calls[0]['rows']))

    @patch('src.volumes.tables.check_docker_running', return_value=True)
    @patch('src.volumes.tables.run_cmd', return_value='container1')
    def test_show_used_volumes(self, *_):
        cb, calls = _table_cb()
        from src.volumes.tables import show_used_volumes
        with patch('src.volumes.tables.async_run', side_effect=self._async_with_df):
            show_used_volumes(cb, self.show_loading)
        self.assertTrue(calls)

    @patch('src.volumes.actions.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.docker.actions.get_sudo_password', return_value=FAKE_PW)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=True)
    @patch('src.utils.utils.run_cmd', return_value='pruned')
    def test_prune_volumes_confirmed(self, mock_run, *_):
        from src.volumes.actions import prune_volumes
        prune_volumes(self.show_output, parent=self.root, show_loading_callback=self.show_loading)
        mock_run.assert_called_once_with(DOCKER_VOLUME_PRUNE, True, FAKE_PW)

    @patch('src.volumes.actions.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=False)
    @patch('src.utils.utils.run_cmd', return_value='')
    def test_prune_volumes_cancelled(self, mock_run, *_):
        from src.volumes.actions import prune_volumes
        prune_volumes(self.show_output, parent=self.root)
        mock_run.assert_not_called()

    @patch('src.volumes.actions.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.docker.actions.get_sudo_password', return_value=FAKE_PW)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=True)
    @patch('src.utils.utils.run_cmd', return_value='deleted')
    def test_delete_all_volumes_confirmed(self, mock_run, *_):
        from src.volumes.actions import delete_all_volumes
        delete_all_volumes(self.show_output, parent=self.root, show_loading_callback=self.show_loading)
        mock_run.assert_called_once_with(DOCKER_VOLUME_RM_ALL, True, FAKE_PW)

    @patch('src.volumes.actions.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=False)
    @patch('src.utils.utils.run_cmd', return_value='')
    def test_delete_all_volumes_cancelled(self, mock_run, *_):
        from src.volumes.actions import delete_all_volumes
        delete_all_volumes(self.show_output, parent=self.root)
        mock_run.assert_not_called()


# ===========================================================================
# 6. Network buttons  (All Networks / Prune)
# ===========================================================================

class TestNetworkButtons(_Base):

    @patch('src.networks.tables.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.networks.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.utils.utils.run_cmd', return_value='abc123\tbridge\tbridge\tlocal')
    def test_show_all_networks(self, *_):
        cb, calls = _table_cb()
        from src.networks.tables import show_networks
        show_networks(cb, self.show_loading)
        self.assertTrue(calls)
        self.assertIn('NETWORK ID', calls[0]['columns'])
        self.assertEqual(len(calls[0]['rows']), 1)

    @patch('src.networks.actions.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.docker.actions.get_sudo_password', return_value=FAKE_PW)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=True)
    @patch('src.utils.utils.run_cmd', return_value='pruned')
    def test_prune_networks_confirmed(self, mock_run, *_):
        from src.networks.actions import prune_networks
        prune_networks(self.show_output, parent=self.root, show_loading_callback=self.show_loading)
        mock_run.assert_called_once_with(DOCKER_NETWORK_PRUNE, True, FAKE_PW)

    @patch('src.networks.actions.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=False)
    @patch('src.utils.utils.run_cmd', return_value='')
    def test_prune_networks_cancelled(self, mock_run, *_):
        from src.networks.actions import prune_networks
        prune_networks(self.show_output, parent=self.root)
        mock_run.assert_not_called()


# ===========================================================================
# 7. Compose buttons  (Projects)
# ===========================================================================

_FAKE_COMPOSE_JSON = (
    '[{"Name":"myapp","Status":"running","ConfigFiles":"/app/docker-compose.yml"}]'
)


class TestComposeButtons(_Base):

    @patch('src.compose.tables.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.compose.tables.get_sudo_password', return_value=FAKE_PW)
    def test_show_compose_projects(self, *_):
        cb, calls = _table_cb()
        from src.compose.tables import show_compose_projects
        with patch('src.compose.tables.async_run',
                   side_effect=lambda *args, **_: args[1](_FAKE_COMPOSE_JSON)):
            show_compose_projects(cb, self.show_loading)
        self.assertTrue(calls)
        self.assertIn('PROJECT', calls[0]['columns'])
        self.assertEqual(len(calls[0]['rows']), 1)
        self.assertEqual(calls[0]['rows'][0][0], 'myapp')

    @patch('src.compose.tables.check_docker_running', return_value=True)
    @patch('src.utils.utils.startThreadForTask', side_effect=_sync_thread)
    @patch('src.compose.tables.get_sudo_password', return_value=FAKE_PW)
    def test_show_compose_projects_empty(self, *_):
        cb, calls = _table_cb()
        from src.compose.tables import show_compose_projects
        with patch('src.compose.tables.async_run',
                   side_effect=lambda *args, **_: args[1]('[]')):
            show_compose_projects(cb, self.show_loading)
        self.assertTrue(calls)
        self.assertEqual(calls[0]['rows'], [])


# ===========================================================================
# 8. Stats buttons  (Container Stats / Disk Storage Simple)
# ===========================================================================

_FAKE_STATS_ROW = 'abc123\tnginx\t0.5%\t50MiB/100MiB\t50%\t1kB/2kB\t1MB/2MB\t5'
_FAKE_DF_SIMPLE = (
    'TYPE            TOTAL   ACTIVE  SIZE      RECLAIMABLE\n'
    'Images          3       2       500MB     200MB (40%)\n'
    'Containers      1       1       10MB      0B (0%)\n'
)


class TestStatsButtons(_Base):

    @patch('src.stats.tables.check_docker_running', return_value=True)
    @patch('src.stats.tables.run_cmd', return_value='abc123')  # running container IDs
    def test_container_stats(self, *_):
        cb, calls = _table_cb()
        from src.stats.tables import show_containers_with_stats
        with patch('src.stats.tables.async_run',
                   side_effect=lambda *args, **_: args[1](_FAKE_STATS_ROW)):
            show_containers_with_stats(cb, self.show_loading)
        self.assertTrue(calls)
        self.assertIn('CPU %', calls[0]['columns'])
        self.assertEqual(len(calls[0]['rows']), 1)

    @patch('src.stats.tables.check_docker_running', return_value=True)
    @patch('src.stats.tables.run_cmd', return_value='')  # no running containers
    def test_container_stats_empty_when_no_containers(self, *_):
        cb, calls = _table_cb()
        from src.stats.tables import show_containers_with_stats
        show_containers_with_stats(cb, self.show_loading)
        self.assertTrue(calls)
        self.assertEqual(calls[0]['rows'], [])

    @patch('src.stats.tables.check_docker_running', return_value=True)
    def test_disk_storage_simple(self, *_):
        cb, calls = _table_cb()
        from src.stats.tables import show_docker_disk_storage_simple
        with patch('src.stats.tables.async_run',
                   side_effect=lambda *args, **_: args[1](_FAKE_DF_SIMPLE)):
            show_docker_disk_storage_simple(cb, self.show_loading)
        self.assertTrue(calls)
        self.assertIn('TYPE', calls[0]['columns'])
        self.assertEqual(len(calls[0]['rows']), 2)
        self.assertEqual(calls[0]['rows'][0][0], 'Images')


# ===========================================================================
# 9. Docker-not-running guard  (every table/action exits early)
# ===========================================================================

class TestDockerNotRunningGuard(_Base):

    @patch('src.containers.tables.check_docker_running', return_value=False)
    @patch('src.utils.utils.run_cmd')
    def test_containers_table_skipped(self, mock_run, _):
        cb, calls = _table_cb()
        from src.containers.tables import show_all_containers
        show_all_containers(cb, self.show_loading)
        mock_run.assert_not_called()
        self.assertEqual(calls, [])

    @patch('src.images.tables.check_docker_running', return_value=False)
    @patch('src.utils.utils.run_cmd')
    def test_images_table_skipped(self, mock_run, _):
        cb, calls = _table_cb()
        from src.images.tables import show_images
        show_images(cb, self.show_loading)
        mock_run.assert_not_called()
        self.assertEqual(calls, [])

    @patch('src.networks.tables.check_docker_running', return_value=False)
    @patch('src.utils.utils.run_cmd')
    def test_networks_table_skipped(self, mock_run, _):
        cb, calls = _table_cb()
        from src.networks.tables import show_networks
        show_networks(cb, self.show_loading)
        mock_run.assert_not_called()
        self.assertEqual(calls, [])

    @patch('src.containers.actions.check_docker_running', return_value=False)
    @patch('src.utils.utils.run_cmd')
    def test_start_all_skipped(self, mock_run, _):
        from src.containers.actions import start_all_containers
        start_all_containers(self.show_output)
        mock_run.assert_not_called()

    @patch('src.volumes.actions.check_docker_running', return_value=False)
    @patch('src.utils.utils.run_cmd')
    def test_prune_volumes_skipped(self, mock_run, _):
        from src.volumes.actions import prune_volumes
        prune_volumes(self.show_output, parent=self.root)
        mock_run.assert_not_called()

    @patch('src.networks.actions.check_docker_running', return_value=False)
    @patch('src.utils.utils.run_cmd')
    def test_prune_networks_skipped(self, mock_run, _):
        from src.networks.actions import prune_networks
        prune_networks(self.show_output, parent=self.root)
        mock_run.assert_not_called()


# ===========================================================================
# 10. Command routing — verify each function issues the correct Docker command
# ===========================================================================

class TestTableCommandRouting(_Base):
    """Each test pins one function to its exact Docker command constant."""

    # --- show_table_command-based (containers, images, networks) ---

    @patch('src.containers.tables.check_docker_running', return_value=True)
    @patch('src.containers.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.containers.tables.show_table_command')
    def test_running_containers_uses_correct_command(self, mock_cmd, *_):
        from src.containers.tables import show_running_containers
        show_running_containers(MagicMock(), self.show_loading)
        self.assertEqual(mock_cmd.call_args[0][0], DOCKER_PS_RUNNING)

    @patch('src.containers.tables.check_docker_running', return_value=True)
    @patch('src.containers.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.containers.tables.show_table_command')
    def test_all_containers_uses_correct_command(self, mock_cmd, *_):
        from src.containers.tables import show_all_containers
        show_all_containers(MagicMock(), self.show_loading)
        self.assertEqual(mock_cmd.call_args[0][0], DOCKER_PS_ALL)

    @patch('src.containers.tables.check_docker_running', return_value=True)
    @patch('src.containers.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.containers.tables.show_table_command')
    def test_stopped_containers_uses_correct_command(self, mock_cmd, *_):
        from src.containers.tables import show_stopped_containers
        show_stopped_containers(MagicMock(), self.show_loading)
        self.assertEqual(mock_cmd.call_args[0][0], DOCKER_PS_STOPPED)

    @patch('src.containers.tables.check_docker_running', return_value=True)
    @patch('src.containers.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.containers.tables.show_table_command')
    def test_paused_containers_uses_correct_command(self, mock_cmd, *_):
        from src.containers.tables import show_paused_containers
        show_paused_containers(MagicMock(), self.show_loading)
        self.assertEqual(mock_cmd.call_args[0][0], DOCKER_PS_PAUSED)

    @patch('src.images.tables.check_docker_running', return_value=True)
    @patch('src.images.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.images.tables.show_table_command')
    def test_images_uses_correct_command(self, mock_cmd, *_):
        from src.images.tables import show_images
        show_images(MagicMock(), self.show_loading)
        self.assertEqual(mock_cmd.call_args[0][0], DOCKER_IMAGES_ALL)

    @patch('src.networks.tables.check_docker_running', return_value=True)
    @patch('src.networks.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.networks.tables.show_table_command')
    def test_networks_uses_correct_command(self, mock_cmd, *_):
        from src.networks.tables import show_networks
        show_networks(MagicMock(), self.show_loading)
        self.assertEqual(mock_cmd.call_args[0][0], DOCKER_NETWORK_LS)

    # --- async_run-based (volumes, compose, disk storage) ---

    @patch('src.volumes.tables.check_docker_running', return_value=True)
    @patch('src.volumes.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.volumes.tables.async_run')
    def test_volumes_uses_correct_command(self, mock_async, *_):
        from src.volumes.tables import show_volumes
        show_volumes(MagicMock(), self.show_loading)
        self.assertEqual(mock_async.call_args[0][0], DOCKER_DISK_USAGE_VERBOSE)

    @patch('src.volumes.tables.check_docker_running', return_value=True)
    @patch('src.volumes.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.volumes.tables.async_run')
    def test_used_volumes_uses_correct_command(self, mock_async, *_):
        from src.volumes.tables import show_used_volumes
        show_used_volumes(MagicMock(), self.show_loading)
        self.assertEqual(mock_async.call_args[0][0], DOCKER_DISK_USAGE_VERBOSE)

    @patch('src.volumes.tables.check_docker_running', return_value=True)
    @patch('src.volumes.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.volumes.tables.async_run')
    def test_unused_volumes_uses_correct_command(self, mock_async, *_):
        from src.volumes.tables import show_unused_volumes
        show_unused_volumes(MagicMock(), self.show_loading)
        self.assertEqual(mock_async.call_args[0][0], DOCKER_DISK_USAGE_VERBOSE)

    @patch('src.compose.tables.check_docker_running', return_value=True)
    @patch('src.compose.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.compose.tables.async_run')
    def test_compose_projects_uses_correct_command(self, mock_async, *_):
        from src.compose.tables import show_compose_projects
        show_compose_projects(MagicMock(), self.show_loading)
        self.assertEqual(mock_async.call_args[0][0], DOCKER_COMPOSE_LS)

    @patch('src.stats.tables.check_docker_running', return_value=True)
    @patch('src.stats.tables.async_run')
    def test_disk_storage_simple_uses_correct_command(self, mock_async, *_):
        from src.stats.tables import show_docker_disk_storage_simple
        show_docker_disk_storage_simple(MagicMock(), self.show_loading)
        self.assertEqual(mock_async.call_args[0][0], DOCKER_DISK_STORAGE_SIMPLE)

    # --- internal run_cmd routing (DOCKER_PS_IDS_RUNNING, DOCKER_PS_IDS_ALL, DOCKER_PS_NAMES_ALL) ---

    @patch('src.stats.tables.check_docker_running', return_value=True)
    @patch('src.stats.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.stats.tables.async_run')  # prevent actual async call
    @patch('src.stats.tables.run_cmd', return_value='abc123')
    def test_container_stats_checks_running_ids(self, mock_run, *_):
        from src.stats.tables import show_containers_with_stats
        show_containers_with_stats(MagicMock(), self.show_loading)
        mock_run.assert_called_once_with(DOCKER_PS_IDS_RUNNING, sudo=True, sudo_password=FAKE_PW)

    @patch('src.stats.tables.check_docker_running', return_value=True)
    @patch('src.stats.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.stats.tables.run_cmd', return_value='abc123')  # running found → triggers async
    @patch('src.stats.tables.async_run')
    def test_container_stats_uses_correct_async_command(self, mock_async, *_):
        from src.stats.tables import show_containers_with_stats
        show_containers_with_stats(MagicMock(), self.show_loading)
        self.assertEqual(mock_async.call_args[0][0], DOCKER_STATS_NO_STREAM)

    @patch('src.images.tables.check_docker_running', return_value=True)
    @patch('src.images.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.images.tables.run_cmd', return_value='')
    def test_unused_images_queries_container_ids(self, mock_run, *_):
        cb, _ = _table_cb()
        from src.images.tables import show_unused_images
        with patch('src.images.tables.async_run',
                   side_effect=lambda *args, **_: args[1](_FAKE_IMAGE_ROWS)):
            show_unused_images(cb, self.show_loading)
        mock_run.assert_called_once_with(DOCKER_PS_IDS_ALL, sudo=True, sudo_password=FAKE_PW)

    @patch('src.images.tables.check_docker_running', return_value=True)
    @patch('src.images.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.images.tables.run_cmd', return_value='')
    def test_used_images_queries_container_ids(self, mock_run, *_):
        cb, _ = _table_cb()
        from src.images.tables import show_used_images
        with patch('src.images.tables.async_run',
                   side_effect=lambda *args, **_: args[1](_FAKE_IMAGE_ROWS)):
            show_used_images(cb, self.show_loading)
        mock_run.assert_called_once_with(DOCKER_PS_IDS_ALL, sudo=True, sudo_password=FAKE_PW)

    @patch('src.volumes.tables.check_docker_running', return_value=True)
    @patch('src.volumes.tables.get_sudo_password', return_value=FAKE_PW)
    @patch('src.volumes.tables.run_cmd', return_value='')
    def test_volumes_callback_queries_container_names(self, mock_run, *_):
        cb, _ = _table_cb()
        from src.volumes.tables import show_volumes
        with patch('src.volumes.tables.async_run',
                   side_effect=lambda *args, **_: args[1](_FAKE_DF_VOLUMES)):
            show_volumes(cb, self.show_loading)
        mock_run.assert_called_once_with(DOCKER_PS_NAMES_ALL, sudo=True, sudo_password=FAKE_PW)


# ===========================================================================
# 11. Clean All Resources  (Stop All → RM All → RMI All → Volume RM All)
# ===========================================================================

class TestCleanAllResources(_Base):

    @patch('src.docker.actions.check_docker_running', return_value=True)
    @patch('src.docker.actions.get_sudo_password', return_value=FAKE_PW)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=True)
    def test_clean_all_runs_full_sequence(self, *_):
        from src.docker.actions import clean_all_resources
        commands_called = []

        def track_async(cmd, cb, **_):
            commands_called.append(cmd)
            cb('')

        with patch('src.docker.actions.async_run', side_effect=track_async):
            clean_all_resources(self.show_output, parent=self.root,
                                show_loading_callback=self.show_loading)

        self.assertIn(DOCKER_STOP_ALL_SAFE, commands_called)
        self.assertIn(DOCKER_RM_ALL_SAFE, commands_called)
        self.assertIn(DOCKER_RMI_ALL_SAFE, commands_called)
        self.assertIn(DOCKER_VOLUME_RM_ALL_SAFE, commands_called)

    @patch('src.docker.actions.check_docker_running', return_value=True)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=False)
    def test_clean_all_cancelled_runs_nothing(self, *_):
        from src.docker.actions import clean_all_resources
        with patch('src.docker.actions.async_run') as mock_async:
            clean_all_resources(self.show_output, parent=self.root)
        mock_async.assert_not_called()


# ===========================================================================
# 12. Delete Used Volumes  (queries LS_IDS and LS_DANGLING before deletion)
# ===========================================================================

class TestDeleteUsedVolumes(_Base):

    @patch('src.volumes.actions.check_docker_running', return_value=True)
    @patch('src.volumes.actions.startThreadForTask', side_effect=_sync_thread)
    @patch('src.volumes.actions.get_sudo_password', return_value=FAKE_PW)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=True)
    def test_delete_used_volumes_queries_correct_commands(self, *_):
        from src.volumes.actions import delete_used_volumes

        # Return values in call order: LS_IDS → LS_DANGLING → rm (deletion)
        with patch('src.volumes.actions.run_cmd',
                   side_effect=['vol1\nvol2', 'vol2', '']) as mock_run:
            delete_used_volumes(self.show_output, parent=self.root,
                                show_loading_callback=self.show_loading)

        issued = [c[0][0] for c in mock_run.call_args_list]
        self.assertIn(DOCKER_VOLUME_LS_IDS, issued)
        self.assertIn(DOCKER_VOLUME_LS_DANGLING, issued)

    @patch('src.volumes.actions.check_docker_running', return_value=True)
    @patch('src.ui.ui_components.confirm_action_dialog', return_value=False)
    def test_delete_used_volumes_cancelled_runs_nothing(self, *_):
        from src.volumes.actions import delete_used_volumes
        with patch('src.volumes.actions.run_cmd') as mock_run:
            delete_used_volumes(self.show_output, parent=self.root)
        mock_run.assert_not_called()


# ===========================================================================
# 13. Selected-item action buttons  (action toolbar for rows selected in tables)
# ===========================================================================

class TestSelectedItemActions(_Base):
    """Tests for action buttons wired to selected table rows via create_selected_item_actions."""

    def setUp(self):
        super().setUp()
        self._common_patches = [
            patch('src.config.config_manager.get_sudo_password', return_value=FAKE_PW),
            patch('src.shared.item_actions.check_docker_running', return_value=True),
        ]
        for p in self._common_patches:
            p.start()

    def tearDown(self):
        for p in self._common_patches:
            p.stop()
        super().tearDown()

    def _dm(self, table_type, row, *, two_rows=False):
        dm = MagicMock()
        items = [MagicMock(), MagicMock()] if two_rows else [MagicMock()]
        dm.get_selected_items.return_value = items
        dm.get_item_values.return_value = row
        dm.current_table_type = table_type
        dm.show_text_output = MagicMock()
        dm.show_table = MagicMock()
        return dm

    def _build(self, dm):
        from src.shared.item_actions import create_selected_item_actions
        btns, _ = create_selected_item_actions(
            ttk.Frame(self.root), self.root, dm, MagicMock(), MagicMock()
        )
        return btns

    # --- Container action buttons ---

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_start_container(self, mock_run):
        btns = self._build(self._dm('container', _F_CONTAINER))
        btns['start'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker start', cmd)
        self.assertIn('c1a2b3c4d5e6', cmd)
        self.assertEqual(
            DOCKER_CONTAINER_START.replace('{containers}', 'c1a2b3c4d5e6'),
            cmd,
        )

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_stop_container(self, mock_run):
        btns = self._build(self._dm('container', _F_CONTAINER))
        btns['stop'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker stop', cmd)
        self.assertIn('c1a2b3c4d5e6', cmd)
        self.assertEqual(
            DOCKER_CONTAINER_STOP.replace('{containers}', 'c1a2b3c4d5e6'),
            cmd,
        )

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_restart_container(self, mock_run):
        btns = self._build(self._dm('container', _F_CONTAINER))
        btns['restart'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker restart', cmd)
        self.assertIn('c1a2b3c4d5e6', cmd)
        self.assertEqual(
            DOCKER_CONTAINER_RESTART.replace('{containers}', 'c1a2b3c4d5e6'),
            cmd,
        )

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_pause_container(self, mock_run):
        btns = self._build(self._dm('container', _F_CONTAINER))
        btns['pause'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker pause', cmd)
        self.assertIn('c1a2b3c4d5e6', cmd)
        self.assertEqual(
            DOCKER_CONTAINER_PAUSE.replace('{containers}', 'c1a2b3c4d5e6'),
            cmd,
        )

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_unpause_container(self, mock_run):
        btns = self._build(self._dm('container', _F_CONTAINER))
        btns['unpause'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker unpause', cmd)
        self.assertIn('c1a2b3c4d5e6', cmd)
        self.assertEqual(
            DOCKER_CONTAINER_UNPAUSE.replace('{containers}', 'c1a2b3c4d5e6'),
            cmd,
        )

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_inspect_container(self, mock_run):
        btns = self._build(self._dm('container', _F_CONTAINER))
        btns['inspect_container'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker inspect', cmd)
        self.assertIn('c1a2b3c4d5e6', cmd)
        self.assertEqual(
            DOCKER_CONTAINER_INSPECT.format(container='c1a2b3c4d5e6'),
            cmd,
        )

    @patch('src.shared.item_actions.confirm_action_dialog', return_value=True)
    @patch('src.shared.item_actions.run_docker_cmd')
    def test_delete_container_confirmed(self, mock_run, *_):
        btns = self._build(self._dm('container', _F_CONTAINER))
        btns['delete'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker rm', cmd)
        self.assertIn('c1a2b3c4d5e6', cmd)
        self.assertEqual(
            DOCKER_CONTAINER_RM.replace('{containers}', 'c1a2b3c4d5e6'),
            cmd,
        )

    @patch('src.shared.item_actions.confirm_action_dialog', return_value=False)
    @patch('src.shared.item_actions.run_docker_cmd')
    def test_delete_container_cancelled(self, mock_run, *_):
        btns = self._build(self._dm('container', _F_CONTAINER))
        btns['delete'].invoke()
        mock_run.assert_not_called()

    # --- Image action buttons ---

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_inspect_image(self, mock_run):
        btns = self._build(self._dm('image', _F_IMAGE))
        btns['inspect_image'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker image inspect', cmd)
        self.assertIn('nginx:latest', cmd)
        self.assertEqual(
            DOCKER_IMAGE_INSPECT.format(image='nginx:latest'),
            cmd,
        )

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_history_image(self, mock_run):
        btns = self._build(self._dm('image', _F_IMAGE))
        btns['history_image'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker history', cmd)
        self.assertIn('nginx:latest', cmd)
        self.assertEqual(
            DOCKER_IMAGE_HISTORY.format(image='nginx:latest'),
            cmd,
        )

    @patch('src.shared.item_actions.confirm_action_dialog', return_value=True)
    @patch('src.shared.item_actions.run_docker_cmd')
    def test_delete_image_confirmed(self, mock_run, *_):
        btns = self._build(self._dm('image', _F_IMAGE))
        btns['delete_image'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker rmi', cmd)
        self.assertIn('img1234567890', cmd)
        self.assertEqual(
            DOCKER_IMAGE_RM.replace('{images}', 'img1234567890'),
            cmd,
        )

    @patch('src.shared.item_actions.confirm_action_dialog', return_value=False)
    @patch('src.shared.item_actions.run_docker_cmd')
    def test_delete_image_cancelled(self, mock_run, *_):
        btns = self._build(self._dm('image', _F_IMAGE))
        btns['delete_image'].invoke()
        mock_run.assert_not_called()

    @patch('tkinter.filedialog.asksaveasfilename', return_value='/tmp/nginx_latest.tar')
    @patch('src.shared.item_actions.run_docker_cmd')
    def test_save_image(self, mock_run, *_):
        btns = self._build(self._dm('image', _F_IMAGE))
        btns['save_image'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker save', cmd)
        self.assertIn('/tmp/nginx_latest.tar', cmd)
        self.assertIn('nginx:latest', cmd)
        self.assertEqual(
            DOCKER_IMAGE_SAVE.format(output_file='/tmp/nginx_latest.tar', image='nginx:latest'),
            cmd,
        )

    # --- Volume action buttons ---

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_inspect_volume(self, mock_run):
        btns = self._build(self._dm('volume', _F_VOLUME))
        btns['inspect_volume'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker volume inspect', cmd)
        self.assertIn('myvol', cmd)
        self.assertEqual(
            DOCKER_VOLUME_INSPECT.format(volume='myvol'),
            cmd,
        )

    @patch('src.shared.item_actions.confirm_action_dialog', return_value=True)
    @patch('src.shared.item_actions.run_docker_cmd')
    def test_delete_volume_confirmed(self, mock_run, *_):
        btns = self._build(self._dm('volume', _F_VOLUME))
        btns['delete_volume'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker volume rm', cmd)
        self.assertIn('myvol', cmd)
        self.assertEqual(
            DOCKER_VOLUME_RM.replace('{volumes}', 'myvol'),
            cmd,
        )

    @patch('src.shared.item_actions.confirm_action_dialog', return_value=False)
    @patch('src.shared.item_actions.run_docker_cmd')
    def test_delete_volume_cancelled(self, mock_run, *_):
        btns = self._build(self._dm('volume', _F_VOLUME))
        btns['delete_volume'].invoke()
        mock_run.assert_not_called()

    # --- Network action buttons ---

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_inspect_network(self, mock_run):
        btns = self._build(self._dm('network', _F_NETWORK))
        btns['inspect_network'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker network inspect', cmd)
        self.assertIn('mynetwork', cmd)
        self.assertEqual(
            DOCKER_NETWORK_INSPECT.format(network='mynetwork'),
            cmd,
        )

    @patch('src.shared.item_actions.confirm_action_dialog', return_value=True)
    @patch('src.shared.item_actions.run_docker_cmd')
    def test_delete_network_confirmed(self, mock_run, *_):
        btns = self._build(self._dm('network', _F_NETWORK))
        btns['delete_network'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker network rm', cmd)
        self.assertIn('mynetwork', cmd)
        self.assertEqual(
            DOCKER_NETWORK_RM.replace('{networks}', 'mynetwork'),
            cmd,
        )

    @patch('src.shared.item_actions.confirm_action_dialog', return_value=False)
    @patch('src.shared.item_actions.run_docker_cmd')
    def test_delete_network_cancelled(self, mock_run, *_):
        btns = self._build(self._dm('network', _F_NETWORK))
        btns['delete_network'].invoke()
        mock_run.assert_not_called()

    # --- stop_using image  (DOCKER_INSPECT_ANCESTOR → DOCKER_CONTAINER_STOP) ---

    @patch('src.shared.item_actions.confirm_action_dialog', return_value=True)
    @patch('src.shared.item_actions.run_docker_cmd')
    @patch('src.shared.item_actions.run_cmd', return_value='cont1\ncont2')
    def test_stop_using_image(self, mock_cmd_run, mock_docker_run, *_):
        btns = self._build(self._dm('image', _F_IMAGE))
        btns['stop_using'].invoke()
        ancestor_cmd = mock_cmd_run.call_args[0][0]
        self.assertIn('docker ps', ancestor_cmd)
        self.assertIn('img1234567890', ancestor_cmd)
        self.assertEqual(
            DOCKER_INSPECT_ANCESTOR.format(image_id='img1234567890'),
            ancestor_cmd,
        )
        stop_cmd = mock_docker_run.call_args[0][0]
        self.assertIn('docker stop', stop_cmd)

    # --- run multi-image  (DOCKER_RUN_DETACHED) ---

    @patch('src.shared.item_actions.confirm_action_dialog', return_value=True)
    @patch('src.shared.item_actions.run_docker_cmd')
    def test_run_multi_image(self, mock_run, *_):
        btns = self._build(self._dm('image', _F_IMAGE, two_rows=True))
        btns['run'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker run', cmd)
        self.assertIn('-d', cmd)
        self.assertIn('nginx:latest', cmd)
        self.assertIn('--restart', cmd)

    # --- Compose action buttons ---

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_compose_up(self, mock_run):
        btns = self._build(self._dm('compose', _F_COMPOSE))
        btns['compose_up'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker compose', cmd)
        self.assertIn('up -d', cmd)
        self.assertIn('docker-compose.yml', cmd)
        self.assertEqual(
            DOCKER_COMPOSE_UP.format(files='-f /app/docker-compose.yml'),
            cmd,
        )

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_compose_down(self, mock_run):
        btns = self._build(self._dm('compose', _F_COMPOSE))
        btns['compose_down'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker compose', cmd)
        self.assertIn('down', cmd)
        self.assertIn('docker-compose.yml', cmd)
        self.assertEqual(
            DOCKER_COMPOSE_DOWN.format(files='-f /app/docker-compose.yml'),
            cmd,
        )

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_compose_restart(self, mock_run):
        btns = self._build(self._dm('compose', _F_COMPOSE))
        btns['compose_restart'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker compose', cmd)
        self.assertIn('restart', cmd)
        self.assertIn('docker-compose.yml', cmd)
        self.assertEqual(
            DOCKER_COMPOSE_RESTART.format(files='-f /app/docker-compose.yml'),
            cmd,
        )

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_compose_logs(self, mock_run):
        btns = self._build(self._dm('compose', _F_COMPOSE))
        btns['compose_logs'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker compose', cmd)
        self.assertIn('logs', cmd)
        self.assertIn('docker-compose.yml', cmd)
        self.assertEqual(
            DOCKER_COMPOSE_LOGS.format(files='-f /app/docker-compose.yml', lines='200'),
            cmd,
        )

    @patch('src.shared.item_actions.async_run')
    def test_compose_services(self, mock_async):
        btns = self._build(self._dm('compose', _F_COMPOSE))
        btns['compose_services'].invoke()
        cmd = mock_async.call_args[0][0]
        self.assertIn('docker compose', cmd)
        self.assertIn('ps', cmd)
        self.assertIn('docker-compose.yml', cmd)
        self.assertEqual(
            DOCKER_COMPOSE_PS.format(files='-f /app/docker-compose.yml'),
            cmd,
        )

    @patch('src.shared.item_actions.run_docker_cmd')
    def test_compose_config(self, mock_run):
        btns = self._build(self._dm('compose', _F_COMPOSE))
        btns['compose_inspect'].invoke()
        cmd = mock_run.call_args[0][0]
        self.assertIn('docker compose', cmd)
        self.assertIn('config', cmd)
        self.assertIn('docker-compose.yml', cmd)
        self.assertEqual(
            DOCKER_COMPOSE_CONFIG.format(files='-f /app/docker-compose.yml'),
            cmd,
        )


# ===========================================================================
# 14. Inspect callback routing  (DOCKER_INSPECT_IMAGE / DOCKER_INSPECT_MOUNTS)
# ===========================================================================

class TestInspectCallbackRouting(_Base):
    """Verifies DOCKER_INSPECT_IMAGE and DOCKER_INSPECT_MOUNTS are used inside async callbacks."""

    @patch('src.images.tables.check_docker_running', return_value=True)
    @patch('src.images.tables.get_sudo_password', return_value=FAKE_PW)
    def test_used_images_callback_uses_inspect_image(self, *_):
        cb, _ = _table_cb()
        from src.images.tables import show_used_images
        fake_images = 'nginx\tlatest\tabc123def456\t100MB'
        with patch('src.images.tables.async_run',
                   side_effect=lambda *args, **_: args[1](fake_images)), \
             patch('src.images.tables.run_cmd',
                   side_effect=['c1a2b3', 'sha256:abc123def456']) as mock_run:
            show_used_images(cb, self.show_loading)
        # First call: PS_IDS_ALL to discover which containers exist
        self.assertEqual(mock_run.call_args_list[0][0][0], DOCKER_PS_IDS_ALL)
        # Second call: DOCKER_INSPECT_IMAGE for each container
        inspect_cmd = mock_run.call_args_list[1][0][0]
        self.assertEqual(inspect_cmd, DOCKER_INSPECT_IMAGE.format(container_id='c1a2b3'))

    @patch('src.volumes.tables.check_docker_running', return_value=True)
    @patch('src.volumes.tables.get_sudo_password', return_value=FAKE_PW)
    def test_volumes_callback_uses_inspect_mounts(self, *_):
        cb, _ = _table_cb()
        from src.volumes.tables import show_volumes
        with patch('src.volumes.tables.async_run',
                   side_effect=lambda *args, **_: args[1](_FAKE_DF_VOLUMES)), \
             patch('src.volumes.tables.run_cmd',
                   side_effect=['mycontainer', '[]']) as mock_run:
            show_volumes(cb, self.show_loading)
        # First call: PS_NAMES_ALL to get container names
        self.assertEqual(mock_run.call_args_list[0][0][0], DOCKER_PS_NAMES_ALL)
        # Second call: DOCKER_INSPECT_MOUNTS for each container name
        mounts_cmd = mock_run.call_args_list[1][0][0]
        self.assertEqual(mounts_cmd, DOCKER_INSPECT_MOUNTS.format(container_name='mycontainer'))


# ===========================================================================
# 15. Dialog command formats  (prompt-based, dialog-based, and dead constants)
# ===========================================================================

class TestDialogCommandFormats(unittest.TestCase):
    """
    Format-string and existence checks for constants that drive dialogs or prompts
    (where end-to-end invocation is blocked by a Toplevel) and for dead constants
    (defined in the module but not currently called by any application code path).
    """

    # --- Prompt-requiring container actions ---

    def test_container_rename_format(self):
        cmd = DOCKER_CONTAINER_RENAME.format(old_name='myapp', new_name='newapp')
        self.assertIn('docker rename', cmd)
        self.assertIn('myapp', cmd)
        self.assertIn('newapp', cmd)

    def test_container_commit_format(self):
        cmd = DOCKER_CONTAINER_COMMIT.format(container='c1a2b3', image='myapp:snapshot')
        self.assertIn('docker commit', cmd)
        self.assertIn('c1a2b3', cmd)
        self.assertIn('myapp:snapshot', cmd)

    # --- Prompt-requiring image actions ---

    def test_image_tag_format(self):
        cmd = DOCKER_IMAGE_TAG.format(source='nginx:latest', target='myrepo/nginx:v1')
        self.assertIn('docker tag', cmd)
        self.assertIn('nginx:latest', cmd)
        self.assertIn('myrepo/nginx:v1', cmd)

    # --- Dialog-based image actions ---

    def test_image_build_format(self):
        cmd = DOCKER_IMAGE_BUILD.format(
            tag='-t myapp:latest ',
            dockerfile='-f Dockerfile ',
            build_args='--build-arg KEY=val ',
            context='/app',
        )
        self.assertIn('docker build', cmd)
        self.assertIn('myapp:latest', cmd)
        self.assertIn('/app', cmd)

    def test_image_load_format(self):
        cmd = DOCKER_IMAGE_LOAD.format(input_file='/tmp/image.tar')
        self.assertIn('docker load', cmd)
        self.assertIn('/tmp/image.tar', cmd)

    def test_image_push_format(self):
        cmd = DOCKER_IMAGE_PUSH.format(image='myrepo/myapp:v1')
        self.assertIn('docker push', cmd)
        self.assertIn('myrepo/myapp:v1', cmd)

    def test_image_save_format(self):
        cmd = DOCKER_IMAGE_SAVE.format(output_file='/tmp/out.tar', image='nginx:latest')
        self.assertIn('docker save', cmd)
        self.assertIn('/tmp/out.tar', cmd)
        self.assertIn('nginx:latest', cmd)

    # --- Search and pull ---

    def test_search_format(self):
        cmd = DOCKER_SEARCH.format(term='nginx')
        self.assertIn('docker search', cmd)
        self.assertIn('nginx', cmd)

    def test_pull_format(self):
        cmd = DOCKER_PULL.format(image_name='nginx:latest')
        self.assertIn('docker pull', cmd)
        self.assertIn('nginx:latest', cmd)

    # --- Volume dialog ---

    def test_volume_create_format(self):
        cmd = DOCKER_VOLUME_CREATE.format(name='myvol')
        self.assertIn('docker volume create', cmd)
        self.assertIn('myvol', cmd)

    # --- Network constants ---

    def test_network_create_format(self):
        cmd = DOCKER_NETWORK_CREATE.format(driver='bridge', options='', name='mynet')
        self.assertIn('docker network create', cmd)
        self.assertIn('bridge', cmd)
        self.assertIn('mynet', cmd)

    def test_network_names_is_ls_command(self):
        self.assertIn('docker network ls', DOCKER_NETWORK_NAMES)

    def test_network_connect_format(self):
        cmd = DOCKER_NETWORK_CONNECT.format(network='mynet', container='c1a2b3')
        self.assertIn('docker network connect', cmd)
        self.assertIn('mynet', cmd)
        self.assertIn('c1a2b3', cmd)

    def test_network_disconnect_format(self):
        cmd = DOCKER_NETWORK_DISCONNECT.format(network='mynet', container='c1a2b3')
        self.assertIn('docker network disconnect', cmd)
        self.assertIn('mynet', cmd)
        self.assertIn('c1a2b3', cmd)

    # --- Dead constants (defined in the file but unused in active code paths) ---

    def test_system_prune_defined(self):
        self.assertIn('docker system prune', DOCKER_SYSTEM_PRUNE)

    def test_container_logs_defined(self):
        self.assertIn('docker logs', DOCKER_CONTAINER_LOGS)

    def test_exec_ls_defined(self):
        self.assertIn('docker exec', DOCKER_EXEC_LS)

    def test_cp_from_defined(self):
        self.assertIn('docker cp', DOCKER_CP_FROM)

    def test_cp_to_defined(self):
        self.assertIn('docker cp', DOCKER_CP_TO)

    def test_images_ids_all_defined(self):
        self.assertIn('docker images', DOCKER_IMAGES_IDS_ALL)


if __name__ == '__main__':
    unittest.main(verbosity=2)
