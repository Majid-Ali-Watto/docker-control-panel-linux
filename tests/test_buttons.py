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
    DOCKER_COMPOSE_UP_BUILD, DOCKER_COMPOSE_BUILD, DOCKER_COMPOSE_PULL, DOCKER_COMPOSE_STOP,
    DOCKER_COMPOSE_DOWN_VOLUMES,
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

    @patch('src.compose.tables.load_compose_projects', return_value=[])
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

    @patch('src.compose.tables.load_compose_projects', return_value=[])
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


class TestComposeRetainedProjects(_Base):

    def _rows(self, saved, listed_json):
        cb, calls = _table_cb()
        from src.compose.tables import show_compose_projects
        with patch('src.compose.tables.check_docker_running', return_value=True), \
             patch('src.compose.tables.get_sudo_password', return_value=FAKE_PW), \
             patch('src.compose.tables.load_compose_projects', return_value=saved), \
             patch('src.compose.tables.async_run', side_effect=lambda *a, **_: a[1](listed_json)):
            show_compose_projects(cb, self.show_loading)
        return calls[0]['rows']

    def test_saved_project_listed_when_not_running(self):
        import os, tempfile
        with tempfile.TemporaryDirectory(prefix='My App') as d:
            f = os.path.join(d, 'docker-compose.yml')
            open(f, 'w').close()
            rows = self._rows([[f]], '[]')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1:], ['not running', f])

    def test_saved_project_not_duplicated_when_running(self):
        import os, tempfile
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, 'docker-compose.yml')
            open(f, 'w').close()
            rows = self._rows([[f]], '[{"Name":"x","Status":"running(1)","ConfigFiles":"%s"}]' % f)
        self.assertEqual([r[0] for r in rows], ['x'])

    def test_saved_project_with_missing_files_hidden(self):
        self.assertEqual(self._rows([['/no/such/dir/docker-compose.yml']], '[]'), [])

    def test_config_round_trip_moves_repeat_to_end(self):
        import tempfile
        from pathlib import Path
        from src.config import config_manager as cm
        with tempfile.TemporaryDirectory() as d, \
             patch.object(cm, 'CONFIG_DIR', Path(d)), patch.object(cm, 'CONFIG_FILE', Path(d) / 'config.json'):
            cm.save_compose_project(['/a/compose.yml'])
            cm.save_compose_project(['/b/compose.yml', '/b/compose.override.yml'])
            cm.save_compose_project(['/a/compose.yml'])
            self.assertEqual(cm.load_compose_projects(),
                             [['/b/compose.yml', '/b/compose.override.yml'], ['/a/compose.yml']])


class TestComposeFolderSelection(unittest.TestCase):

    def _folder(self, names):
        import os, tempfile
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        for n in names:
            open(os.path.join(d.name, n), 'w').close()
        return d.name

    def test_picks_default_file_and_matching_override(self):
        import os
        from src.compose.dialogs import _compose_files_in_folder
        d = self._folder(['docker-compose.yml', 'docker-compose.override.yml', 'compose.override.yaml'])
        self.assertEqual(_compose_files_in_folder(d),
                         [os.path.join(d, 'docker-compose.yml'), os.path.join(d, 'docker-compose.override.yml')])

    def test_compose_yaml_takes_precedence(self):
        import os
        from src.compose.dialogs import _compose_files_in_folder
        d = self._folder(['docker-compose.yml', 'compose.yaml'])
        self.assertEqual(_compose_files_in_folder(d), [os.path.join(d, 'compose.yaml')])

    def test_folder_without_compose_file(self):
        from src.compose.dialogs import _compose_files_in_folder
        self.assertEqual(_compose_files_in_folder(self._folder(['README.md'])), [])


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

    def _compose_cmd(self, button):
        with patch('src.shared.item_actions.run_docker_cmd') as mock_run:
            self._build(self._dm('compose', _F_COMPOSE))[button].invoke()
        return mock_run.call_args[0][0] if mock_run.called else None

    def test_compose_up_build_build_pull_stop(self):
        files = '-f /app/docker-compose.yml'
        for button, template in (('compose_up_build', DOCKER_COMPOSE_UP_BUILD),
                                 ('compose_build', DOCKER_COMPOSE_BUILD),
                                 ('compose_pull', DOCKER_COMPOSE_PULL),
                                 ('compose_stop', DOCKER_COMPOSE_STOP)):
            self.assertEqual(self._compose_cmd(button), template.format(files=files), button)
        self.assertIn('up -d --build', DOCKER_COMPOSE_UP_BUILD)

    @patch('src.shared.item_actions.confirm_action_dialog', return_value=True)
    def test_compose_down_volumes_confirmed(self, mock_confirm):
        cmd = self._compose_cmd('compose_down_volumes')
        self.assertEqual(cmd, DOCKER_COMPOSE_DOWN_VOLUMES.format(files='-f /app/docker-compose.yml'))
        self.assertIn('down -v', cmd)
        mock_confirm.assert_called_once()

    @patch('src.shared.item_actions.confirm_action_dialog', return_value=False)
    def test_compose_down_volumes_declined_runs_nothing(self, _):
        self.assertIsNone(self._compose_cmd('compose_down_volumes'))

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


# ===========================================================================
# 16. Table usability  (sorting, search, selection-aware buttons, in-place refresh)
# ===========================================================================

class _TableFixture(_Base):
    """A DisplayManager wired to a real Treeview and the real row-action buttons."""
    COLS = ["CONTAINER ID", "NAMES", "IMAGE", "STATUS", "PORTS", "SIZE"]
    ROWS = [["c1", "web", "nginx", "Up 2 hours", "80/tcp", "1B"],
            ["c2", "db", "pg", "Exited (0) 3 days ago", "", "2B"],
            ["c3", "cache", "redis", "Up 1 hour (Paused)", "", "3B"]]

    def setUp(self):
        super().setUp()
        from src.ui.ui_display import DisplayManager
        from src.shared.item_actions import create_selected_item_actions
        out = ttk.Frame(self.root)
        table_frame = ttk.Frame(out)
        self.tree = ttk.Treeview(table_frame)
        self.tree.pack()
        action_frame = ttk.Frame(table_frame)
        text_frame = ttk.Frame(out)
        self.dm = DisplayManager(out, table_frame, text_frame, self.tree, tk.Text(text_frame), action_frame)
        self.btns, label = create_selected_item_actions(action_frame, self.root, self.dm, MagicMock(), MagicMock())
        self.dm.set_action_buttons(self.btns, label)
        self.dm.show_table(self.COLS, self.ROWS, 'container', "All Containers")

    def _names(self):
        return [self.tree.item(i)['values'][2] for i in self.tree.get_children()]


_FAKE_DF_VERBOSE = '''Images space usage:

REPOSITORY   TAG       IMAGE ID       CREATED        SIZE      SHARED SIZE   UNIQUE SIZE   CONTAINERS
nginx        latest    abc123def456   2 weeks ago    187MB     0B            187MB         1
redis        7         fff000fff000   About an hour ago   20MB   0B           20MB          0

Containers space usage:

CONTAINER ID   IMAGE     COMMAND                  LOCAL VOLUMES   SIZE      CREATED       STATUS       NAMES
c1c1c1c1c1c1   nginx     "/docker-entrypoint.\u2026"   0               1.09kB    2 weeks ago   Up 2 weeks   web

Local Volumes space usage:

VOLUME NAME   LINKS     SIZE
data          1         10MB

Build cache usage: 0B

CACHE ID   CACHE TYPE   SIZE      CREATED   LAST USED   USAGE     SHARED
'''


class TestDiskUsageView(_TableFixture):

    def _open(self):
        from src.stats import dialogs
        with patch('src.stats.dialogs.check_docker_running', return_value=True), \
             patch('src.stats.dialogs.async_run', side_effect=lambda *a, **_: a[1](_FAKE_DF_VERBOSE)):
            dialogs.docker_disk_usage_view(self.dm, MagicMock())

    def test_parses_all_four_sections(self):
        from src.stats.dialogs import _parse_sections
        sections = _parse_sections(_FAKE_DF_VERBOSE)
        self.assertEqual(list(sections), ["Images", "Containers", "Volumes", "Build Cache"])
        self.assertEqual(len(sections["Images"][1]), 2)
        self.assertEqual(sections["Volumes"][1], [["data", "1", "10MB"]])
        self.assertEqual(sections["Build Cache"][1], [])

    def test_each_tab_is_a_searchable_sortable_table_with_actions(self):
        self._open()
        self.assertEqual(self.dm.current_table_type, 'disk_images')
        self.assertIsNotNone(self.dm.search_entry)
        self.dm.sort_by(4)   # SIZE: 20MB before 187MB
        self.assertEqual([self.tree.item(i)['values'][1] for i in self.tree.get_children()], ["redis", "nginx"])
        self.assertEqual([n for n, _ in self.dm._visible_action_buttons],
                         ['delete_image', 'inspect_image', 'history_image'])

    def test_switching_tabs_keeps_choice_across_reload(self):
        self._open()
        strip = self.dm._chrome[0].winfo_children()[0]
        next(b for b in strip.winfo_children() if b.cget('text') == 'Volumes').invoke()
        self.assertEqual(self.dm.current_table_type, 'disk_volumes')
        self.assertEqual(self.tree.item(self.tree.get_children()[0])['values'][1], 'data')
        self._open()   # reload (e.g. after a delete) stays on Volumes
        self.assertEqual(self.dm.current_table_type, 'disk_volumes')

    def test_image_delete_works_from_images_tab(self):
        from src.stats import dialogs
        dialogs._active_tab["label"] = "Images"
        self._open()
        self.tree.selection_set('0')
        self.dm.update_selection_state()
        with patch('src.shared.item_actions.run_docker_cmd') as mock_run, \
             patch('src.shared.item_actions.check_docker_running', return_value=True), \
             patch('src.shared.item_actions.confirm_action_dialog', return_value=True):
            self.btns['delete_image'].invoke()
        self.assertIn('abc123def456', mock_run.call_args[0][0])

    def test_relative_ages_sort_by_age(self):
        self.dm._sort_col = 0
        ages = ["2 weeks ago", "About an hour ago", "3 days ago", "10 minutes ago"]
        ordered = sorted(ages, key=lambda a: self.dm._sort_key([a]))   # oldest first
        self.assertEqual(ordered, ["2 weeks ago", "3 days ago", "About an hour ago", "10 minutes ago"])


class TestTableUsability(_TableFixture):

    def test_stats_tables_get_search_and_sort(self):
        cols = ["CONTAINER ID", "NAME", "CPU %", "MEM USAGE"]
        rows = [["a", "web", "5.00%", "10MiB / 1GiB"], ["b", "db", "20.00%", "2MiB / 1GiB"]]
        self.dm.show_table(cols, rows, 'container_stats', "Container Stats")
        self.assertIsNotNone(self.dm.search_entry)
        self.dm.sort_by(2)
        self.dm.sort_by(2)   # second click: descending
        self.assertEqual([self.tree.item(i)['values'][2] for i in self.tree.get_children()], ["db", "web"])
        self.dm.search_entry.insert(0, "web")
        self.dm.perform_search()
        self.assertEqual(len(self.tree.get_children()), 1)

    def test_reload_of_same_view_keeps_search_box(self):
        cols = ["CONTAINER ID", "NAME"]
        self.dm.show_table(cols, [["a", "web"]], 'container_stats', "Container Stats")
        entry = self.dm.search_entry
        entry.insert(0, "we")
        self.dm.show_table(cols, [["a", "web"], ["b", "db"]], 'container_stats', "Container Stats")
        self.assertIs(self.dm.search_entry, entry)
        self.assertEqual(entry.get(), "we")
        self.assertEqual(len(self.tree.get_children()), 1)

    def test_actions_disabled_until_rows_selected(self):
        self.assertTrue(self.btns['start'].instate(['disabled']))
        self.tree.selection_set('0')
        self.dm.update_selection_state()
        self.assertFalse(self.btns['start'].instate(['disabled']))

    def test_single_row_actions_disabled_for_multi_select(self):
        self.tree.selection_set('0', '1')
        self.dm.update_selection_state()
        self.assertFalse(self.btns['start'].instate(['disabled']))
        self.assertTrue(self.btns['rename'].instate(['disabled']))

    def test_sort_toggles_direction(self):
        self.dm.sort_by(1)
        self.assertEqual(self._names(), ['cache', 'db', 'web'])
        self.dm.sort_by(1)
        self.assertEqual(self._names(), ['web', 'db', 'cache'])

    def test_search_filters_rows(self):
        self.dm.search_entry.insert(0, 'redis')
        self.dm.perform_search()
        self.assertEqual(self._names(), ['cache'])

    def test_reload_keeps_search_and_selection(self):
        self.dm.search_entry.insert(0, 'e')
        self.dm.perform_search()
        self.tree.selection_set(self.tree.get_children()[0])
        self.dm.show_table(self.COLS, self.ROWS, 'container', "All Containers")
        self.assertEqual(self.dm.search_entry.get(), 'e')
        self.assertEqual(len(self.tree.selection()), 1)

    def test_rows_use_only_alternating_stripe_tags(self):
        tags = {tag for i in self.tree.get_children() for tag in self.tree.item(i)['tags']}
        self.assertEqual(tags, {'oddrow', 'evenrow'})

    def test_text_output_offers_back_to_list(self):
        self.dm.view_refresh = MagicMock()
        self.dm.show_text_output("details")
        self.assertTrue(self.dm._back_bar.winfo_manager())
        self.dm.refresh_view()
        self.dm.view_refresh.assert_called_once()


class TestDateFilterAndSort(_TableFixture):
    """Tables with a CREATED column get a date/time filter and a sort dropdown."""
    COLS = ["CONTAINER ID", "NAMES", "STATUS", "CREATED"]

    def setUp(self):
        from datetime import datetime, timedelta
        now = datetime.now()
        fmt = lambda d: d.strftime("%Y-%m-%d %H:%M:%S") + " +0500 PKT"
        self.ROWS = [["c1", "new", "Up", fmt(now - timedelta(minutes=10))],
                     ["c2", "mid", "Up", fmt(now - timedelta(days=3))],
                     ["c3", "old", "Exited", fmt(now - timedelta(days=60))]]
        super().setUp()
        self.dm.show_table(self.COLS, self.ROWS, 'container', "All Containers")

    def test_parses_docker_timestamps(self):
        from src.ui.ui_display import DisplayManager as D
        self.assertEqual(D._parse_row_date("2026-10-15 15:06:49 +0500 PKT").hour, 15)
        self.assertEqual(D._parse_row_date("2026-10-13 02:34:04.770160954 +0500 PKT").minute, 34)
        self.assertIsNone(D._parse_row_date(""))

    def test_preset_filters_by_age(self):
        self.dm._apply_filters("Last 24 hours", "", "")
        self.assertEqual(self._names(), ['new'])
        self.dm._apply_filters("Last 30 days", "", "")
        self.assertEqual(self._names(), ['new', 'mid'])

    def test_custom_range_from_to(self):
        from datetime import datetime, timedelta
        day = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        self.dm._apply_filters("Custom range", day, day)
        self.assertEqual(self._names(), ['mid'])

    def test_clear_filters_restores_rows(self):
        self.dm._apply_filters("Last hour", "", "")
        self.dm._clear_filters()
        self.assertEqual(len(self._names()), 3)

    def _open_popup(self):
        self.dm._filter_btn.invoke()
        popup = self.dm._filter_popup
        popup.update()
        return popup

    def _buttons(self, popup):
        found = {}
        def walk(w):
            for c in w.winfo_children():
                if isinstance(c, ttk.Button):
                    found[c.cget("text")] = c
                walk(c)
        walk(popup)
        return found

    def test_filter_button_opens_popup_under_it_and_toggles(self):
        btn = self.dm._filter_btn
        self.assertIsNotNone(btn)
        popup = self._open_popup()
        self.assertGreaterEqual(popup.winfo_rooty(), btn.winfo_rooty() + btn.winfo_height())
        btn.invoke()
        self.assertFalse(popup.winfo_exists())

    def test_popup_changes_wait_for_apply(self):
        popup = self._open_popup()
        popup._preset.set("Last 24 hours")
        popup._sync_custom_rows()
        self.assertEqual(len(self._names()), 3)
        self._buttons(popup)["Apply"].invoke()
        self.assertEqual(self._names(), ['new'])
        self.assertFalse(popup.winfo_exists())
        self.assertIn("●", self.dm._filter_btn.cget("text"))

    def test_popup_prefills_current_filter_and_clear_resets_it(self):
        self.dm._apply_filters("Last hour", "", "")
        popup = self._open_popup()
        self.assertEqual(popup._preset.get(), "Last hour")
        self._buttons(popup)["Clear filters"].invoke()
        self.assertEqual(len(self._names()), 3)
        self.assertEqual(self.dm._preset_var.get(), "Any time")
        self.assertNotIn("●", self.dm._filter_btn.cget("text"))

    def test_custom_range_rows_only_for_custom_and_non_custom_drops_dates(self):
        popup = self._open_popup()
        self.assertEqual(popup._custom.winfo_manager(), "")
        popup._preset.set("Custom range")
        popup._sync_custom_rows()
        self.assertEqual(popup._custom.winfo_manager(), "grid")
        popup._from.set("2020-01-01")
        popup._preset.set("Last hour")
        self._buttons(popup)["Apply"].invoke()
        self.assertEqual(self.dm._from_var.get(), "")

    def test_outside_click_and_escape_close_popup(self):
        self.root.deiconify()   # a withdrawn window cannot hand keyboard focus to its popup
        popup = self._open_popup()
        self.dm._dismiss_filter_popup(MagicMock(widget=self.tree))
        self.assertFalse(popup.winfo_exists())
        popup = self._open_popup()
        popup.focus_force()
        popup.update()
        popup.event_generate("<Escape>")
        popup.update()
        self.assertFalse(popup.winfo_exists())

    def test_reload_closes_popup(self):
        popup = self._open_popup()
        self.dm.show_table(self.COLS, self.ROWS, 'container', "All Containers")
        self.assertFalse(popup.winfo_exists())

    def test_no_filter_button_without_date_column(self):
        self.dm.show_table(["VOLUME NAME"], [["v1"]], 'volume', "Volumes")
        self.assertIsNone(self.dm._filter_btn)

    def test_sort_dropdown_created_is_newest_first(self):
        self.dm._sort_var.set("CREATED")
        self.dm._on_sort_selected()
        self.assertEqual(self._names(), ['new', 'mid', 'old'])
        self.dm._toggle_sort_order()
        self.assertEqual(self._names(), ['old', 'mid', 'new'])

    def test_header_click_updates_sort_dropdown(self):
        self.dm.sort_by(1)
        self.assertEqual(self.dm._sort_var.get(), "NAMES")


class TestSortByValue(_TableFixture):
    """Sorting compares sizes, percentages, numbers and names by value, not as plain text."""
    COLS = ["REPOSITORY", "SIZE", "CPU %", "NAMES"]
    ROWS = [["a", "1.1GB", "0.50%", "web10"],
            ["b", "2GB", "12.00%", "web2"],
            ["c", "13MB", "3.00%", "Web1"],
            ["d", "25.9kB", "", ""],
            ["e", "1.47GB", "100.00%", "db"],
            ["f", "0B", "0.10%", "api"]]

    def _col(self, index):
        return [self.tree.item(i)['values'][index] for i in self.tree.get_children()]

    def test_sizes_sort_by_bytes_large_to_small(self):
        self.dm.sort_by(1)
        self.dm.sort_by(1)
        self.assertEqual(self._col(2), ['2 GB', '1.47 GB', '1.1 GB', '13 MB', '25.9 kB', '0 B'])

    def test_sizes_sort_small_to_large(self):
        self.dm.sort_by(1)
        self.assertEqual(self._col(2), ['0 B', '25.9 kB', '13 MB', '1.1 GB', '1.47 GB', '2 GB'])

    def test_percentages_sort_numerically(self):
        self.dm.sort_by(2)
        self.assertEqual(self._col(3), ['0.10%', '0.50%', '3.00%', '12.00%', '100.00%', self.dm.EMPTY_CELL])

    def test_empty_cells_stay_last_in_both_directions(self):
        self.dm.sort_by(2)
        self.assertEqual(self._col(1)[-1], 'd')
        self.dm.sort_by(2)
        self.assertEqual(self._col(1)[-1], 'd')

    def test_names_sort_case_insensitive_with_numbers_in_order(self):
        self.dm.sort_by(3)
        self.assertEqual(self._col(4), ['api', 'db', 'Web1', 'web2', 'web10', self.dm.EMPTY_CELL])

    def test_binary_and_decimal_units(self):
        from src.ui.ui_display import DisplayManager as D
        probe = type("P", (), {"_sort_col": 0, "_date_col": None, "_SIZE": D._SIZE, "_NUMBER": D._NUMBER,
                                  "_AGE": D._AGE, "_AGE_SECONDS": D._AGE_SECONDS})()
        key = lambda v: D._sort_key(probe, [v])
        self.assertEqual(key("1KiB"), key("1024B"))
        self.assertLess(key("1kB"), key("1KiB"))
        self.assertLess(key("98.3kB (virtual 236MB)"), key("1MB"))
        self.assertLess(key("12.5MiB / 7.6GiB"), key("1GB"))

    def test_date_upper_bound_covers_whole_minute(self):
        from datetime import datetime
        from src.ui.ui_display import DisplayManager as D
        self.assertEqual(D._parse_user_date("2026-10-15 15:06", end_of_day=True), datetime(2026, 10, 15, 15, 6, 59))
        self.assertEqual(D._parse_user_date("2026-10-15 15:06"), datetime(2026, 10, 15, 15, 6))


class TestRoundedHelpers(_Base):
    """src/ui/rounded.py: layout rewriting and the Canvas-backed rounded surfaces."""

    def test_swap_element_replaces_border_and_keeps_children(self):
        from src.ui.rounded import _swap_element
        layout = [('Button.border', {'border': '1', 'sticky': 'nswe',
                                     'children': [('Button.label', {'sticky': 'nswe'})]})]
        out = _swap_element(layout, 'Button.border', 'Rounded0.Button.border')
        name, opts = out[0]
        self.assertEqual(name, 'Rounded0.Button.border')
        self.assertNotIn('border', opts)
        self.assertEqual(opts['children'][0][0], 'Button.label')

    def test_swap_element_replaces_inherited_rounded_element(self):
        from src.ui.rounded import _swap_element
        layout = [('Rounded3.Button.border', {'sticky': 'nswe'})]
        out = _swap_element(layout, 'Button.border', 'Rounded9.Button.border')
        self.assertEqual(out[0][0], 'Rounded9.Button.border')

    def test_readable_keeps_legible_colours_and_fixes_weak_ones(self):
        from src.ui.rounded import readable, on_fill, contrast
        self.assertEqual(readable("#ffffff", "#222222"), "#ffffff")
        self.assertGreaterEqual(contrast(readable("#00bc8c", "#ffffff"), "#ffffff"), 4.5)   # accent on light
        self.assertGreaterEqual(contrast(readable("#6e40c0", "#190831"), "#190831"), 4.5)   # accent on dark
        self.assertGreaterEqual(contrast(readable("#888888", "#e9ecef"), "#e9ecef"), 4.5)
        self.assertEqual(on_fill("#00bc8c", "#ffffff"), "#000000")   # white on bright green is 2.4:1
        self.assertEqual(on_fill("#375a7f", "#ffffff"), "#ffffff")

    def test_badge_grows_with_its_text(self):
        from src.ui.rounded import RoundedBadge
        badge = RoundedBadge(self.root, text="1")
        badge.pack()
        self.root.update_idletasks()
        narrow = badge.winfo_reqwidth()
        badge.set_text("38 of 38 containers")
        self.root.update_idletasks()
        self.assertGreater(badge.winfo_reqwidth(), narrow)

    def test_make_remembers_colours_for_theme_changes(self):
        from src.ui import rounded
        label = rounded.make(tk.Label, self.root, text="x", bg="#0d1117", fg="#ffffff")
        label.configure(bg="#ffffff")            # what a theme switch does to tk widgets
        rounded.refresh_panels()
        self.assertEqual(label.cget("bg"), "#0d1117")


class TestDateTimePicker(_TableFixture):
    """Calendar + time picker used by the custom date range."""
    COLS = ["CONTAINER ID", "NAMES", "STATUS", "CREATED"]
    ROWS = [["c1", "mid", "Up", "2026-03-10 12:30:00 +0500 PKT"],
            ["c2", "late", "Up", "2026-03-10 23:59:30 +0500 PKT"],
            ["c3", "old", "Exited", "2026-01-05 08:00:00 +0500 PKT"]]

    def setUp(self):
        super().setUp()
        self.dm.show_table(self.COLS, self.ROWS, 'container', "All Containers")

    def _picker(self, initial=None):
        from src.ui.datetime_picker import DateTimePicker
        return DateTimePicker(self.root, initial=initial)

    def test_selecting_a_day_and_time_returns_that_datetime(self):
        from datetime import datetime, date
        picker = self._picker(datetime(2026, 3, 10, 9, 5))
        picker._select(date(2026, 3, 12))
        picker._hour.set("17")
        picker._minute.set("45")
        picker._ok()
        self.assertEqual(picker.result, datetime(2026, 3, 12, 17, 45))

    def test_month_navigation_wraps_years(self):
        from datetime import datetime
        picker = self._picker(datetime(2026, 12, 15, 0, 0))
        picker._shift_month(1)
        self.assertEqual((picker._year, picker._month), (2027, 1))
        picker._shift_month(-13)
        self.assertEqual((picker._year, picker._month), (2025, 12))
        picker.destroy()

    def test_out_of_range_time_is_clamped(self):
        from datetime import datetime
        picker = self._picker(datetime(2026, 3, 10, 0, 0))
        picker._hour.set("99")
        picker._minute.set("abc")
        self.assertEqual(picker.selected_datetime(), datetime(2026, 3, 10, 23, 0))
        picker.destroy()

    def test_clear_returns_empty_string_and_cancel_returns_none(self):
        picker = self._picker()
        picker._clear()
        self.assertEqual(picker.result, "")
        picker = self._picker()
        picker.destroy()
        self.assertIsNone(picker.result)

    @patch('src.ui.ui_display.pick_datetime')
    def test_picked_values_fill_the_range_and_filter(self, mock_pick):
        from datetime import datetime
        mock_pick.return_value = datetime(2026, 3, 10, 0, 0)
        self.dm._pick_date(self.dm._from_var, end_of_day=False)
        mock_pick.return_value = datetime(2026, 3, 10, 23, 59)
        self.dm._pick_date(self.dm._to_var, end_of_day=True)
        self.assertEqual(self.dm._from_var.get(), "2026-03-10 00:00")
        self.assertEqual(self.dm._to_var.get(), "2026-03-10 23:59")
        self.dm._apply_filters("Custom range", self.dm._from_var.get(), self.dm._to_var.get())
        # "To 23:59" covers the whole minute, so the 23:59:30 row is included
        names = [self.tree.item(i)['values'][2] for i in self.tree.get_children()]
        self.assertEqual(names, ['mid', 'late'])

    @patch('src.ui.ui_display.pick_datetime', return_value=None)
    def test_cancelled_picker_changes_nothing(self, _):
        self.dm._from_var.set("2026-03-10")
        self.dm._pick_date(self.dm._from_var, end_of_day=False)
        self.assertEqual(self.dm._from_var.get(), "2026-03-10")


class TestMutationFeedback(_Base):
    """State-changing row actions keep the table and refresh it; failures show details."""

    def _run(self, output):
        dm = MagicMock()
        dm.get_selected_items.return_value = [MagicMock()]
        dm.get_item_values.return_value = _F_CONTAINER
        dm.current_table_type = 'container'
        from src.shared.item_actions import create_selected_item_actions
        with patch('src.config.config_manager.get_sudo_password', return_value=FAKE_PW), \
             patch('src.shared.item_actions.check_docker_running', return_value=True), \
             patch('src.shared.item_actions.run_docker_cmd') as mock_run:
            # run root.after callbacks inline so no Tk event loop (and its stale timers) is needed
            root = MagicMock()
            root.after.side_effect = lambda _ms, fn: fn()
            btns, _ = create_selected_item_actions(ttk.Frame(self.root), root, dm, MagicMock(), MagicMock())
            btns['start'].invoke()
            mock_run.call_args.kwargs['callback'](output)
        return dm

    def test_success_refreshes_in_place(self):
        dm = self._run("c1a2b3c4d5e6")
        dm.refresh_view.assert_called_once()
        dm.show_text_output.assert_not_called()
        self.assertEqual(dm.set_status.call_args[0][1], "success")

    def test_failure_shows_output(self):
        dm = self._run("Error response from daemon: No such container: x")
        dm.refresh_view.assert_not_called()
        dm.show_text_output.assert_called_once()
        self.assertEqual(dm.set_status.call_args[0][1], "error")


# ===========================================================================
# 17. Table cells  (empty-value placeholder, cell selection + copy, row actions)
# ===========================================================================

class TestFormatCell(unittest.TestCase):

    def setUp(self):
        from src.ui.cell_format import format_cell
        self.fmt = format_cell

    def test_dates(self):
        self.assertEqual(self.fmt("CREATED", "2026-10-14 12:40:02 +0500 PKT"), "14 Oct 2026, 12:40")
        self.assertEqual(self.fmt("CREATED", "2026-10-13 02:34:04.770160954 +0500 PKT"), "13 Oct 2026, 02:34")
        self.assertEqual(self.fmt("CREATED", "2 weeks ago"), "2 weeks ago")        # already readable
        self.assertEqual(self.fmt("CREATED", ""), "")

    def test_sizes_get_a_space_before_the_unit(self):
        self.assertEqual(self.fmt("SIZE", "2.74MB (virtual 388MB)"), "2.74 MB (virtual 388 MB)")
        self.assertEqual(self.fmt("SIZE", "0B"), "0 B")
        self.assertEqual(self.fmt("MEM USAGE", "12.5MiB / 7.6GiB"), "12.5 MiB / 7.6 GiB")
        self.assertEqual(self.fmt("RECLAIMABLE", "1.2GB (45%)"), "1.2 GB (45%)")
        self.assertEqual(self.fmt("SIZE", "1.1 GB"), "1.1 GB")                      # no double space

    def test_size_rule_only_applies_to_size_columns(self):
        self.assertEqual(self.fmt("NAMES", "web1b"), "web1b")
        self.assertEqual(self.fmt("IMAGE", "app2MB"), "app2MB")

    def test_ports_drop_wildcard_addresses_and_duplicates(self):
        self.assertEqual(self.fmt("PORTS", "0.0.0.0:8080->80/tcp, [::]:8080->80/tcp, 443/tcp"),
                         "8080 → 80/tcp, 443/tcp")
        self.assertEqual(self.fmt("PORTS", "127.0.0.1:5432->5432/tcp, :::5432->5432/tcp"),
                         "127.0.0.1:5432 → 5432/tcp, 5432 → 5432/tcp")
        self.assertEqual(self.fmt("PORTS", ""), "")

    def test_compose_status_and_files(self):
        import os
        self.assertEqual(self.fmt("STATUS", "running(2), exited(1)"), "running (2), exited (1)")
        self.assertEqual(self.fmt("STATUS", "Exited (137) 25 hours ago"), "Exited (137) 25 hours ago")
        home = os.path.expanduser("~")
        self.assertEqual(self.fmt("CONFIG FILES", f"{home}/a/x.yml,/tmp/y.yml"), "~/a/x.yml, /tmp/y.yml")


class TestPopupMenu(_Base):

    def setUp(self):
        super().setUp()
        from src.ui.popup_menu import PopupMenu
        # Pointer events only reach mapped widgets, so map the window but keep it invisible and
        # off-screen (and never grab the input focus from the user's real windows)
        self.root.geometry("400x300+-5000+-5000")
        try:
            self.root.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        self.root.deiconify()
        self.root.update()
        self.calls = []
        self.menu = PopupMenu(self.root)
        self.entries = [("First", lambda: self.calls.append("first"), True),
                        None,
                        ("Off", lambda: self.calls.append("off"), False),
                        ("Last", lambda: self.calls.append("last"), True)]
        self.menu.show(self.entries, 10, 10, backdrop="#222222")
        self.root.update()

    def _rows(self):
        return [e[0] for e in self.menu._entries]

    def _click(self, widget, press=True):
        if press:
            widget.event_generate("<ButtonPress-1>", x=3, y=3)
        widget.event_generate("<ButtonRelease-1>", x=3, y=3)

    def test_opens_with_one_row_per_enabled_entry(self):
        self.assertTrue(self.menu.is_open)
        self.assertEqual([r.cget("text") for r in self._rows()], ["First", "Last"])

    def test_left_click_runs_the_entry_and_closes(self):
        self._click(self._rows()[1])
        self.assertEqual(self.calls, ["last"])
        self.assertFalse(self.menu.is_open)

    def test_release_without_a_press_on_the_entry_does_nothing(self):
        self._click(self._rows()[0], press=False)                  # e.g. a drag that ended here
        self.assertEqual(self.calls, [])
        self.assertTrue(self.menu.is_open)

    def test_wheel_and_other_buttons_do_not_pick_entries(self):
        row = self._rows()[0]
        for button in (2, 3, 4, 5):
            row.event_generate(f"<ButtonPress-{button}>", x=3, y=3)
            row.event_generate(f"<ButtonRelease-{button}>", x=3, y=3)
        row.event_generate("<MouseWheel>", x=3, y=3, delta=120)
        self.assertEqual(self.calls, [])

    def test_wheel_over_the_menu_does_not_close_it(self):
        self._rows()[0].event_generate("<ButtonPress-5>", x=3, y=3)
        self.assertTrue(self.menu.is_open)

    def test_click_elsewhere_closes_it_without_running_anything(self):
        self.root.event_generate("<ButtonPress-1>", x=1, y=1)
        self.assertFalse(self.menu.is_open)
        self.assertEqual(self.calls, [])

    def test_escape_closes_it(self):
        self.assertTrue(self.root.bind_all("<Escape>"))               # bound for the whole app
        self.menu._on_escape(None)    # generated key events need real X focus, so call the handler
        self.assertFalse(self.menu.is_open)

    def test_arrow_keys_and_enter_choose_an_entry_skipping_disabled_ones(self):
        for key in ("<Up>", "<Down>", "<Return>", "<space>"):
            self.assertTrue(self.menu._holder.bind(key), key)         # keys are wired to the popup
        self.menu._move(1); self.menu._move(1)                        # first, then last (Off is skipped)
        self.menu._activate(self.menu._active)
        self.assertEqual(self.calls, ["last"])
        self.assertFalse(self.menu.is_open)

    def test_hover_highlights_one_entry_at_a_time(self):
        first, last = self._rows()
        first.event_generate("<Enter>"); last.event_generate("<Enter>")
        self.assertNotEqual(str(first.cget("bg")), str(last.cget("bg")))

    def test_menu_slides_up_to_stay_inside_the_window(self):
        self.menu.show(self.entries, self.root.winfo_rootx() + 20, self.root.winfo_rooty() + 290)
        self.root.update()
        holder = self.menu._holder
        self.assertLessEqual(holder.winfo_y() + holder.winfo_reqheight(), self.root.winfo_height())
        self.assertGreaterEqual(holder.winfo_y(), 0)

    def test_reopening_replaces_the_previous_menu(self):
        old = self.menu._holder
        self.menu.show(self.entries, 20, 20)
        self.root.update()
        self.assertFalse(old.winfo_exists())
        self.assertTrue(self.menu.is_open)

    def test_closed_panels_do_not_pile_up_in_the_rounded_registry(self):
        from src.ui import rounded
        before = len(rounded._panels)
        for _ in range(3):
            self.menu.show(self.entries, 10, 10)
        self.menu.close()
        self.assertLessEqual(len(rounded._panels), before)


class TestTableCells(_TableFixture):

    def _cell(self, row, column):
        """Make a cell active the way a click would (the withdrawn test window has no geometry)."""
        iid = str(row)
        self.tree.selection_set(iid)
        self.dm.cells.iid, self.dm.cells.col = iid, f"#{self.COLS.index(column) + 2}"

    def test_empty_values_show_a_placeholder(self):
        ports = [self.tree.item(i)['values'][5] for i in self.tree.get_children()]
        self.assertEqual(ports, ["80/tcp", self.dm.EMPTY_CELL, self.dm.EMPTY_CELL])

    def test_whitespace_only_value_counts_as_empty(self):
        self.dm.show_table(self.COLS, [["c1", "web", "nginx", "Up", "  ", "1B"]], 'container', "All Containers")
        self.assertEqual(self.tree.item("0")['values'][5], self.dm.EMPTY_CELL)

    def test_row_values_keep_real_blanks_for_actions(self):
        self.assertEqual(self.dm.get_item_values("1"), [2, "c2", "db", "pg", "Exited (0) 3 days ago", "", "2B"])

    def test_search_does_not_match_the_placeholder(self):
        self.dm.search_entry.insert(0, self.dm.EMPTY_CELL)
        self.dm.perform_search()
        self.assertEqual(self.tree.get_children(), ())

    def test_cell_value_is_raw_text_with_column_name(self):
        self._cell(1, "NAMES")
        self.assertEqual(self.dm.cells.value(), ("NAMES", "db"))
        self._cell(1, "PORTS")
        self.assertEqual(self.dm.cells.value(), ("PORTS", ""))     # copies '', never the placeholder

    def test_no_active_cell_has_no_value(self):
        self.assertIsNone(self.dm.cells.value())

    def test_active_cell_follows_its_row_through_a_reload_and_sort(self):
        self._cell(0, "NAMES")                                      # web
        self.dm.sort_by(1)                                          # NAMES ascending: cache, db, web
        self.assertEqual(self.dm.cells.iid, "2")
        self.assertEqual(self.dm.cells.value(), ("NAMES", "web"))

    def test_active_cell_is_dropped_when_its_row_disappears(self):
        self._cell(0, "NAMES")
        self.dm.show_table(self.COLS, self.ROWS[1:], 'container', "All Containers")
        self.assertIsNone(self.dm.cells.iid)

    def test_selected_rows_text_has_header_and_shown_values(self):
        self.tree.selection_set(["1"])
        self.assertEqual(self.dm.selected_rows_text().split("\n"),
                         ["No.\tCONTAINER ID\tNAMES\tIMAGE\tSTATUS\tPORTS\tSIZE",
                          "2\tc2\tdb\tpg\tExited (0) 3 days ago\t\t2 B"])

    def test_row_actions_list_the_toolbar_actions_with_enabled_state(self):
        self.tree.selection_set("0")
        self.dm.update_selection_state()
        actions = {label: enabled for label, _, enabled in self.dm.row_actions()}
        self.assertEqual(len(actions), len(self.dm._visible_action_buttons))
        self.assertTrue(any(actions.values()))
        self.tree.selection_set("0", "1")
        self.dm.update_selection_state()
        multi = {label: enabled for label, _, enabled in self.dm.row_actions()}
        self.assertFalse(all(multi.values()))                       # single-row actions are off

    def test_dates_show_in_a_readable_form_but_still_sort_and_filter(self):
        cols = ["NAME", "CREATED"]
        rows = [["old", "2026-05-17 00:19:23.734200882 +0500 PKT"], ["new", "2026-10-15 10:45:32 +0500 PKT"]]
        self.dm.show_table(cols, rows, 'network', "Networks")
        self.dm.sort_by(1)
        self.assertEqual([self.tree.item(i)['values'][2] for i in self.tree.get_children()],
                         ["17 May 2026, 00:19", "15 Oct 2026, 10:45"])
        self.assertEqual(self.dm.get_item_values("1")[2], "2026-10-15 10:45:32 +0500 PKT")   # actions keep raw
        self.dm.search_entry.insert(0, "oct 2026")                # searches what is shown
        self.dm.perform_search()
        self.assertEqual(len(self.tree.get_children()), 1)

    def test_cell_copy_gives_the_shown_text(self):
        self.dm.show_table(["NAME", "CREATED"], [["n", "2026-10-15 10:45:32 +0500 PKT"]], 'network', "Networks")
        self.tree.selection_set("0")
        self.dm.cells.iid, self.dm.cells.col = "0", "#3"
        self.assertEqual(self.dm.cells.value(), ("CREATED", "15 Oct 2026, 10:45"))

    def test_select_all_rows_selects_only_the_rows_shown(self):
        self.dm.select_all_rows()
        self.assertEqual(set(self.tree.selection()), {"0", "1", "2"})
        self.dm.search_entry.insert(0, "redis")
        self.dm.perform_search()
        self.tree.selection_set(())
        self.dm.select_all_rows()
        self.assertEqual(len(self.tree.selection()), 1)

    def _right_click(self):
        """Right-click the first row; returns the PopupMenu the table's context menu opens."""
        from src.shared.context_menus import setup_table_context_menu
        from src.ui import popup_menu
        shown = []
        original = popup_menu.PopupMenu.show
        with patch.object(popup_menu.PopupMenu, 'show',
                          lambda m, entries, *a, **k: (shown.append((m, entries)), original(m, entries, *a, **k))[1]):
            setup_table_context_menu(self.dm, self.root)
            event = dict(x=5, y=5, rootx=5, rooty=5)
            with patch.object(self.tree, 'identify_region', return_value="cell"), \
                 patch.object(self.tree, 'identify_row', return_value="0"), \
                 patch.object(self.tree, 'identify_column', return_value="#3"):
                self.tree.event_generate("<ButtonPress-3>", **event)
        return shown[0]

    def test_right_click_leaves_the_menu_open(self):
        """The same click also reaches the app-wide 'click elsewhere closes it' handler."""
        menu, _entries = self._right_click()
        self.root.update()
        self.assertTrue(menu.is_open)

    def test_a_later_click_elsewhere_still_closes_it(self):
        menu, _entries = self._right_click()
        self.root.event_generate("<ButtonPress-1>", x=1, y=1)
        self.assertFalse(menu.is_open)

    def test_context_menu_offers_select_all_and_row_actions(self):
        _menu, entries = self._right_click()
        labels = [e[0] for e in entries if e]
        self.assertIn("Select All Rows (Ctrl+A)", labels)
        self.assertIn("Close menu", labels)
        self.assertIn("Copy NAMES: web", labels)
        self.assertTrue(any("Start" in label for label in labels))
        self.assertIn(None, entries)                                  # separators between groups

    def _double_click(self, action):
        btn = self.btns[action]
        btn.invoke = MagicMock()
        self.tree.selection_set("0")
        self.dm.update_selection_state()
        with patch.object(self.tree, 'identify_region', return_value="cell"):
            self.dm._on_double_click(MagicMock(x=5, y=5))
        return btn

    def test_double_click_opens_details(self):
        self._double_click('inspect_container').invoke.assert_called_once()

    def test_double_click_does_nothing_when_the_action_is_disabled(self):
        self.tree.selection_set(())
        self.dm.update_selection_state()
        btn = self.btns['inspect_container']
        btn.invoke = MagicMock()
        with patch.object(self.tree, 'identify_region', return_value="cell"):
            self.dm._on_double_click(MagicMock(x=5, y=5))
        btn.invoke.assert_not_called()

    def test_double_click_on_the_heading_does_nothing(self):
        btn = self.btns['inspect_container']
        btn.invoke = MagicMock()
        self.tree.selection_set("0")
        self.dm.update_selection_state()
        with patch.object(self.tree, 'identify_region', return_value="heading"):
            self.dm._on_double_click(MagicMock(x=5, y=5))
        btn.invoke.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)


class TestCommandsReference(unittest.TestCase):
    """The Commands tab data: complete, unique and flattened for copy / download."""

    def test_reference_commands_are_described_and_unique(self):
        from src.help.help_commands import COMMAND_SECTIONS
        commands = [c for _, items in COMMAND_SECTIONS for c, d in items if d]
        self.assertEqual(len(commands), sum(len(items) for _, items in COMMAND_SECTIONS))
        self.assertEqual(len(commands), len(set(commands)))

    def test_every_command_constant_is_listed_with_a_description(self):
        """Adding a constant to commands.py without describing it fails here."""
        import re
        from src.docker import commands
        from src.help.help_commands import APP_COMMAND_SECTIONS, _DESCRIPTIONS, _display_template
        names = [n for n in dir(commands) if re.fullmatch(r"DOCKER_[A-Z0-9_]+", n)]
        self.assertEqual([n for n in names if n not in _DESCRIPTIONS], [])
        self.assertEqual([n for n in _DESCRIPTIONS if n not in names], [])
        listed = {c for _, items in APP_COMMAND_SECTIONS for c, _d in items}
        for name in names:
            self.assertIn(_display_template(name, getattr(commands, name)), listed, name)

    def test_app_commands_have_descriptions_and_no_repeats(self):
        from src.help.help_commands import APP_COMMAND_SECTIONS
        items = [i for _, section in APP_COMMAND_SECTIONS for i in section]
        self.assertTrue(all(d for _c, d in items))
        commands = [c for c, _d in items]
        self.assertEqual(len(commands), len(set(commands)))

    def test_compose_commands_are_listed_with_and_without_a_file(self):
        from src.help.help_commands import APP_COMMAND_SECTIONS, COMMAND_SECTIONS, _display_variants
        self.assertEqual([c for c, _d in _display_variants("X", "docker compose {files} up -d", "Up")],
                         ["docker compose up -d", "docker compose -f <file.yml> up -d"])
        app = {c for _, items in APP_COMMAND_SECTIONS for c, _d in items}
        for needed in ("docker compose up -d", "docker compose -f <file.yml> up -d", "docker compose down -v",
                       "docker compose logs --tail <lines>", "docker compose config"):
            self.assertIn(needed, app)
        reference = {c for _, items in COMMAND_SECTIONS for c, _d in items}
        for needed in ("docker compose up", "docker compose up -d", "docker compose up --build",
                       "docker compose up -d --build", "docker compose down", "docker compose logs -f",
                       "docker compose exec <service> sh", "docker compose -f <a.yml> -f <b.yml> up -d"):
            self.assertIn(needed, reference)

    def test_reference_covers_every_group_with_its_variants(self):
        from src.help.help_commands import COMMAND_SECTIONS
        reference = {c for _, items in COMMAND_SECTIONS for c, _d in items}
        for needed in (
            "docker ps -a", "docker ps -a --filter status=exited", "docker run -d --name <name> <image>",
            "docker run -it --rm <image> sh", "docker run -d -p <host>:<container> <image>",
            "docker run -d --restart unless-stopped <image>", "docker exec -it <container> bash",
            "docker logs -f --tail 100 <container>", "docker rm -f <container>", "docker container prune -f",
            "docker images -a", "docker pull <image>:<tag>", "docker build -t <name:tag> -f <Dockerfile> .",
            "docker build --no-cache -t <name:tag> .", "docker rmi -f <image>", "docker image prune -a",
            "docker volume ls --filter dangling=true", "docker volume create <name>", "docker volume prune -a",
            "docker network create --subnet <cidr> <name>", "docker network connect <network> <container>",
            "docker network prune -f", "docker system prune -a --volumes", "docker builder prune",
            "docker events --filter type=container", "systemctl enable --now docker", "journalctl -u docker -f",
            "sudo usermod -aG docker $USER",
        ):
            self.assertIn(needed, reference)

    def test_templates_are_shown_readably(self):
        from src.help.help_commands import _display_template
        self.assertEqual(_display_template("X", "docker stop {containers}"), "docker stop <containers>")
        self.assertEqual(_display_template("X", "docker compose {files} up -d"), "docker compose -f <file.yml> up -d")
        self.assertEqual(_display_template("X", "docker inspect --format='{{{{.Image}}}}' {c}"),
                         "docker inspect --format='{{.Image}}' <c>")
        self.assertEqual(_display_template("X", "docker ps --format '{{.ID}}\t{{.Names}}'"),
                         "docker ps --format '{{.ID}}\\t{{.Names}}'")

    def test_app_service_and_inline_commands_are_listed(self):
        from src.help.help_commands import commands_as_text
        text = commands_as_text()
        for needed in ("systemctl start docker.socket docker.service", "systemctl is-active docker",
                       "docker exec -it <container> /bin/sh", "docker logs [-t] --follow <container>",
                       "docker run -d --restart <policy>"):
            self.assertIn(needed, text)

    def test_text_export_contains_every_command(self):
        from src.help.help_commands import APP_COMMAND_SECTIONS, COMMAND_SECTIONS, commands_as_text
        text = commands_as_text()
        for sections in (APP_COMMAND_SECTIONS, COMMAND_SECTIONS):
            for _, items in sections:
                for command, description in items:
                    self.assertIn(command, text)
                    self.assertIn(description, text)
