"""
Action buttons for selected items in tables (containers, images, volumes, networks, compose).
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.config.config_manager import get_sudo_password
from src.config.config_tooltips import ACTION_TOOLTIPS
from src.docker.actions import check_docker_running
from src.docker.operations import run_docker_cmd
from src.docker.commands import (
    DOCKER_CONTAINER_START, DOCKER_CONTAINER_STOP, DOCKER_CONTAINER_RESTART,
    DOCKER_CONTAINER_RM, DOCKER_CONTAINER_PAUSE, DOCKER_CONTAINER_UNPAUSE,
    DOCKER_CONTAINER_RENAME, DOCKER_CONTAINER_COMMIT, DOCKER_CONTAINER_INSPECT,
    DOCKER_IMAGE_RM, DOCKER_IMAGE_PUSH, DOCKER_IMAGE_TAG, DOCKER_IMAGE_SAVE, DOCKER_IMAGE_HISTORY,
    DOCKER_IMAGE_INSPECT, DOCKER_VOLUME_RM, DOCKER_VOLUME_INSPECT,
    DOCKER_NETWORK_RM, DOCKER_NETWORK_INSPECT, DOCKER_NETWORK_CONNECT,
    DOCKER_NETWORK_DISCONNECT, DOCKER_COMPOSE_UP, DOCKER_COMPOSE_DOWN,
    DOCKER_COMPOSE_UP_BUILD, DOCKER_COMPOSE_BUILD, DOCKER_COMPOSE_PULL, DOCKER_COMPOSE_STOP,
    DOCKER_COMPOSE_DOWN_VOLUMES,
    DOCKER_COMPOSE_RESTART, DOCKER_COMPOSE_LOGS, DOCKER_COMPOSE_CONFIG,
    DOCKER_COMPOSE_PS, DOCKER_INSPECT_ANCESTOR, DOCKER_NETWORK_NAMES,
    DOCKER_RUN_DETACHED,
)
from src.ui.ui_components import Tooltip, confirm_action_dialog
from src.utils.utils import run_cmd, async_run
from src.shared.helpers import (
    _quote, _join_quoted, _join_flag_values, _split_csv_lines,
    _compose_files_to_args, _center_dialog, _make_output_callback, is_error_output,
)
import shlex


# Table types a row action accepts: the dedicated list plus the Docker Disk Usage tabs, whose
# rows start with the same identifying columns (container ID / image repo+tag+ID / volume name)
_CONTAINER_VIEWS = ('container', 'container_stats', 'disk_containers')
_IMAGE_VIEWS = ('image', 'disk_images')
_VOLUME_VIEWS = ('volume', 'disk_volumes')


def create_selected_item_actions(action_frame, root, display_manager, refresh_images_callback, show_loading_callback=None):
    """Create action buttons for selected items in tables"""

    def _selected_rows(resource_name, table_type=None, allow_multiple=True):
        selection = display_manager.get_selected_items()
        if not selection:
            messagebox.showwarning("No Selection", f"Please select {resource_name} from the table")
            return None
        if table_type:
            allowed_types = table_type if isinstance(table_type, (tuple, list, set)) else (table_type,)
            if display_manager.current_table_type not in allowed_types:
                expected = ', '.join(allowed_types)
                messagebox.showwarning("Wrong View", f"Select {resource_name} from the {expected} table.")
                return None
        if not allow_multiple and len(selection) > 1:
            messagebox.showwarning("Multiple Selection", f"Please select only one {resource_name}.")
            return None
        return [display_manager.get_item_values(item) for item in selection]

    def _run_output_command(command, title):
        """Read-only commands (inspect, logs, history): show the output as text."""
        run_docker_cmd(
            command,
            sudo=True,
            sudo_password=get_sudo_password(),
            callback=_make_output_callback(display_manager.show_text_output, title, None, root),
            loading_callback=show_loading_callback,
        )

    def _run_mutation(command, title):
        """Commands that change state: keep the table on screen, report the result in the
        status bar and reload the list in place. Failures show the full output instead."""
        def on_done(result):
            def finish():
                if is_error_output(result):
                    display_manager.show_text_output(f"{title} failed\n\n{result}".strip())
                    display_manager.set_status(f"✖ {title} failed — details shown above", "error")
                else:
                    display_manager.set_status(f"✔ {title} done", "success")
                    display_manager.refresh_view()
            root.after(0, finish)

        run_docker_cmd(
            command,
            sudo=True,
            sudo_password=get_sudo_password(),
            callback=on_done,
            loading_callback=show_loading_callback,
        )

    def _prompt_value(title, label, initial_value=""):
        dialog = tk.Toplevel(root)
        dialog.title(title)
        dialog.transient(root)
        dialog.grab_set()

        result = {'value': None}
        ttk.Label(dialog, text=label, font=("Arial", 10)).pack(padx=20, pady=(20, 8), anchor="w")
        value_var = tk.StringVar(value=initial_value)
        entry = ttk.Entry(dialog, textvariable=value_var, width=42)
        entry.pack(padx=20, pady=4)
        entry.focus()

        def on_ok():
            value = value_var.get().strip()
            if value:
                result['value'] = value
                dialog.destroy()
            else:
                messagebox.showwarning("Input Required", "Please enter a value.", parent=dialog)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(10, 20))
        ttk.Button(btn_frame, text="OK", style="primary.TButton", command=on_ok, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)

        entry.bind("<Return>", lambda e: on_ok())
        entry.bind("<Escape>", lambda e: dialog.destroy())
        _center_dialog(dialog, min_width=360)
        dialog.wait_window()
        return result['value']

    def _container_ids(rows):
        return [row[1] for row in rows]

    def _container_name(row):
        return row[2]

    def _image_ref(row):
        repo = row[1]
        tag = row[2]
        image_id = row[3]
        if repo == "<none>" or tag == "<none>":
            return image_id
        return f"{repo}:{tag}"

    def _network_name(row):
        return row[2]

    def _compose_project(row):
        return row[1], row[3]

    def start_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=_CONTAINER_VIEWS)
        if not rows:
            return
        _run_mutation(
            DOCKER_CONTAINER_START.format(containers=_join_quoted(_container_ids(rows))),
            "Container Start",
        )

    def stop_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=_CONTAINER_VIEWS)
        if not rows:
            return
        _run_mutation(
            DOCKER_CONTAINER_STOP.format(containers=_join_quoted(_container_ids(rows))),
            "Container Stop",
        )

    def restart_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=_CONTAINER_VIEWS)
        if not rows:
            return
        _run_mutation(
            DOCKER_CONTAINER_RESTART.format(containers=_join_quoted(_container_ids(rows))),
            "Container Restart",
        )

    def pause_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=_CONTAINER_VIEWS)
        if not rows:
            return
        _run_mutation(
            DOCKER_CONTAINER_PAUSE.format(containers=_join_quoted(_container_ids(rows))),
            "Container Pause",
        )

    def unpause_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=_CONTAINER_VIEWS)
        if not rows:
            return
        _run_mutation(
            DOCKER_CONTAINER_UNPAUSE.format(containers=_join_quoted(_container_ids(rows))),
            "Container Unpause",
        )

    def rename_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=_CONTAINER_VIEWS, allow_multiple=False)
        if not rows:
            return
        new_name = _prompt_value("Rename Container", "New container name:", _container_name(rows[0]))
        if not new_name:
            return
        _run_mutation(
            DOCKER_CONTAINER_RENAME.format(old_name=_quote(rows[0][1]), new_name=_quote(new_name)),
            "Container Rename",
        )

    def delete_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=_CONTAINER_VIEWS)
        if not rows:
            return
        count = len(rows)
        msg = f"Delete {count} container(s)?" if count > 1 else f"Delete container {rows[0][1]}?"
        if confirm_action_dialog(root, "Confirm", msg):
            _run_mutation(
                DOCKER_CONTAINER_RM.format(containers=_join_quoted(_container_ids(rows))),
                "Container Delete",
            )

    def inspect_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=_CONTAINER_VIEWS, allow_multiple=False)
        if not rows:
            return
        _run_output_command(
            DOCKER_CONTAINER_INSPECT.format(container=_quote(rows[0][1])),
            "Container Inspect",
        )

    def commit_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=_CONTAINER_VIEWS, allow_multiple=False)
        if not rows:
            return
        image_ref = _prompt_value("Commit Container", "New image name (e.g. myapp:snapshot):")
        if not image_ref:
            return
        _run_mutation(
            DOCKER_CONTAINER_COMMIT.format(container=_quote(rows[0][1]), image=_quote(image_ref)),
            "Container Commit",
        )

    def delete_selected_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type=_IMAGE_VIEWS)
        if not rows:
            return
        count = len(rows)
        msg = f"Delete {count} image(s)?" if count > 1 else f"Delete image {_image_ref(rows[0])}?"
        if confirm_action_dialog(root, "Confirm", msg):
            _run_mutation(
                DOCKER_IMAGE_RM.format(images=' '.join(_quote(row[3]) for row in rows)),
                "Image Delete",
            )

    def tag_selected_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type='image', allow_multiple=False)
        if not rows:
            return
        target_tag = _prompt_value("Tag Image", "New tag (e.g. repo:tag):")
        if not target_tag:
            return
        _run_mutation(
            DOCKER_IMAGE_TAG.format(source=_quote(_image_ref(rows[0])), target=_quote(target_tag)),
            "Image Tag",
        )

    def push_selected_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type='image', allow_multiple=False)
        if not rows:
            return
        from src.images.dialogs import push_image_dialog
        push_image_dialog(root, image_ref=_image_ref(rows[0]), refresh_callback=refresh_images_callback)

    def save_selected_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type='image', allow_multiple=False)
        if not rows:
            return
        filename = filedialog.asksaveasfilename(
            parent=root,
            defaultextension=".tar",
            filetypes=[("Tar archives", "*.tar"), ("All files", "*.*")],
            initialfile=f"{rows[0][1].replace('/', '_')}_{rows[0][2]}.tar",
        )
        if not filename:
            return
        _run_mutation(
            DOCKER_IMAGE_SAVE.format(output_file=_quote(filename), image=_quote(_image_ref(rows[0]))),
            "Image Save",
        )

    def inspect_selected_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type=_IMAGE_VIEWS, allow_multiple=False)
        if not rows:
            return
        _run_output_command(
            DOCKER_IMAGE_INSPECT.format(image=_quote(_image_ref(rows[0]))),
            "Image Inspect",
        )

    def history_selected_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type=_IMAGE_VIEWS, allow_multiple=False)
        if not rows:
            return
        _run_output_command(
            DOCKER_IMAGE_HISTORY.format(image=_quote(_image_ref(rows[0]))),
            "Image History",
        )

    def delete_selected_volume():
        if not check_docker_running(): return
        rows = _selected_rows("volume", table_type=_VOLUME_VIEWS)
        if not rows:
            return
        count = len(rows)
        msg = f"Delete {count} volume(s)?" if count > 1 else f"Delete volume {rows[0][1]}?"
        if confirm_action_dialog(root, "Confirm", msg):
            _run_mutation(
                DOCKER_VOLUME_RM.format(volumes=' '.join(_quote(row[1]) for row in rows)),
                "Volume Delete",
            )

    def inspect_selected_volume():
        if not check_docker_running(): return
        rows = _selected_rows("volume", table_type=_VOLUME_VIEWS, allow_multiple=False)
        if not rows:
            return
        _run_output_command(
            DOCKER_VOLUME_INSPECT.format(volume=_quote(rows[0][1])),
            "Volume Inspect",
        )

    def delete_selected_network():
        if not check_docker_running(): return
        rows = _selected_rows("network", table_type='network')
        if not rows:
            return
        count = len(rows)
        msg = f"Delete {count} network(s)?" if count > 1 else f"Delete network {_network_name(rows[0])}?"
        if confirm_action_dialog(root, "Confirm", msg):
            _run_mutation(
                DOCKER_NETWORK_RM.format(networks=' '.join(_quote(_network_name(row)) for row in rows)),
                "Network Delete",
            )

    def inspect_selected_network():
        if not check_docker_running(): return
        rows = _selected_rows("network", table_type='network', allow_multiple=False)
        if not rows:
            return
        _run_output_command(
            DOCKER_NETWORK_INSPECT.format(network=_quote(_network_name(rows[0]))),
            "Network Inspect",
        )

    def connect_selected_network():
        if not check_docker_running(): return
        rows = _selected_rows("network", table_type='network', allow_multiple=False)
        if not rows:
            return
        container_ref = _prompt_value("Connect Network", "Container name or ID:")
        if not container_ref:
            return
        _run_mutation(
            DOCKER_NETWORK_CONNECT.format(network=_quote(_network_name(rows[0])), container=_quote(container_ref)),
            "Network Connect",
        )

    def disconnect_selected_network():
        if not check_docker_running(): return
        rows = _selected_rows("network", table_type='network', allow_multiple=False)
        if not rows:
            return
        container_ref = _prompt_value("Disconnect Network", "Container name or ID:")
        if not container_ref:
            return
        _run_mutation(
            DOCKER_NETWORK_DISCONNECT.format(network=_quote(_network_name(rows[0])), container=_quote(container_ref)),
            "Network Disconnect",
        )

    def run_container_from_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type='image')
        if not rows:
            return

        images = [_image_ref(row) for row in rows]

        if len(images) > 1:
            count = len(images)
            msg = f"Run container(s) from {count} selected image(s)?"
            if confirm_action_dialog(root, "Confirm", msg):
                commands = ' && '.join(
                    DOCKER_RUN_DETACHED.format(
                        restart_policy="unless-stopped",
                        name="",
                        ports="",
                        envs="",
                        volumes="",
                        network="",
                        extra_args="",
                        image=f" {_quote(image)}",
                        command="",
                    )
                    for image in images
                )
                _run_mutation(commands, "Container Run")
            return

        dialog = tk.Toplevel(root)
        dialog.title("Run Container")
        dialog.transient(root)
        dialog.grab_set()

        ttk.Label(dialog, text=f"Image: {images[0]}", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 10))

        name_var = tk.StringVar()
        restart_var = tk.StringVar(value="unless-stopped")
        network_names = [name for name in run_cmd(DOCKER_NETWORK_NAMES, sudo=True, sudo_password=get_sudo_password()).splitlines() if name.strip()]
        network_var = tk.StringVar(value="")
        command_var = tk.StringVar()

        ttk.Label(dialog, text="Container name:", font=("Arial", 10)).grid(row=1, column=0, sticky="w", padx=16, pady=4)
        ttk.Entry(dialog, textvariable=name_var, width=42).grid(row=1, column=1, sticky="ew", padx=16, pady=4)

        ttk.Label(dialog, text="Restart policy:", font=("Arial", 10)).grid(row=2, column=0, sticky="w", padx=16, pady=4)
        ttk.Combobox(dialog, textvariable=restart_var, values=["unless-stopped", "always", "on-failure", "no"], state="readonly", width=42).grid(row=2, column=1, sticky="ew", padx=16, pady=4)

        ttk.Label(dialog, text="Network:", font=("Arial", 10)).grid(row=3, column=0, sticky="w", padx=16, pady=4)
        ttk.Combobox(dialog, textvariable=network_var, values=[""] + network_names, state="readonly", width=42).grid(row=3, column=1, sticky="ew", padx=16, pady=4)

        ttk.Label(dialog, text="Ports (one per line, e.g. 8080:80):", font=("Arial", 10)).grid(row=4, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 4))
        ports_text = tk.Text(dialog, height=3, width=50, font=("JetBrains Mono", 9))
        ports_text.grid(row=5, column=0, columnspan=2, sticky="ew", padx=16, pady=4)

        ttk.Label(dialog, text="Environment (KEY=VALUE):", font=("Arial", 10)).grid(row=6, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 4))
        env_text = tk.Text(dialog, height=3, width=50, font=("JetBrains Mono", 9))
        env_text.grid(row=7, column=0, columnspan=2, sticky="ew", padx=16, pady=4)

        ttk.Label(dialog, text="Volumes (source:/target):", font=("Arial", 10)).grid(row=8, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 4))
        volume_text = tk.Text(dialog, height=3, width=50, font=("JetBrains Mono", 9))
        volume_text.grid(row=9, column=0, columnspan=2, sticky="ew", padx=16, pady=4)

        ttk.Label(dialog, text="Command override (optional):", font=("Arial", 10)).grid(row=10, column=0, sticky="w", padx=16, pady=4)
        ttk.Entry(dialog, textvariable=command_var, width=42).grid(row=10, column=1, sticky="ew", padx=16, pady=4)

        dialog.columnconfigure(1, weight=1)

        def on_run():
            ports = _split_csv_lines(ports_text.get("1.0", tk.END))
            envs = _split_csv_lines(env_text.get("1.0", tk.END))
            volumes = _split_csv_lines(volume_text.get("1.0", tk.END))

            command_tail = ""
            custom_command = command_var.get().strip()
            if custom_command:
                try:
                    command_tail = " " + ' '.join(_quote(part) for part in shlex.split(custom_command))
                except ValueError as exc:
                    messagebox.showwarning("Invalid Command", f"Could not parse command override: {exc}", parent=dialog)
                    return

            command = DOCKER_RUN_DETACHED.format(
                restart_policy=_quote(restart_var.get().strip() or "unless-stopped"),
                name=f" --name {_quote(name_var.get().strip())}" if name_var.get().strip() else "",
                ports=_join_flag_values("-p", ports),
                envs=_join_flag_values("-e", envs),
                volumes=_join_flag_values("-v", volumes),
                network=f" --network {_quote(network_var.get().strip())}" if network_var.get().strip() else "",
                extra_args="",
                image=f" {_quote(images[0])}",
                command=command_tail,
            )
            dialog.destroy()
            _run_mutation(command, "Container Run")

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=11, column=0, columnspan=2, pady=(12, 16))
        ttk.Button(btn_frame, text="Run", style="primary.TButton", command=on_run, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)

        _center_dialog(dialog, min_width=640)

    def stop_containers_using_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type='image')
        if not rows:
            return

        all_containers = []
        for row in rows:
            containers = run_cmd(DOCKER_INSPECT_ANCESTOR.format(image_id=row[3]), sudo=True, sudo_password=get_sudo_password())
            if containers:
                all_containers.extend(containers.splitlines())

        all_containers = [container for container in all_containers if container.strip()]
        if not all_containers:
            messagebox.showinfo("Info", "No containers found using selected image(s)")
            return

        count = len(all_containers)
        msg = f"Stop {count} container(s) using selected image(s)?"
        if confirm_action_dialog(root, "Confirm", msg):
            _run_mutation(
                DOCKER_CONTAINER_STOP.format(containers=_join_quoted(all_containers)),
                "Stop Containers Using Image",
            )

    def _compose_mutation(template, title, confirm_msg=None):
        """Run one compose command (built from `template`) for every selected project."""
        if not check_docker_running(): return
        rows = _selected_rows("compose project", table_type='compose')
        if not rows:
            return
        commands = []
        for row in rows:
            _project_name, files = _compose_project(row)
            files_arg = _compose_files_to_args(files)
            if files_arg:
                commands.append(template.format(files=files_arg))
        if not commands:
            return
        if confirm_msg and not confirm_action_dialog(
                root, "Confirm", confirm_msg.format(projects=', '.join(r[1] for r in rows))):
            return
        _run_mutation(' && '.join(commands), title)

    def compose_up_selected():
        _compose_mutation(DOCKER_COMPOSE_UP, "Compose Up")

    def compose_up_build_selected():
        _compose_mutation(DOCKER_COMPOSE_UP_BUILD, "Compose Up --build")

    def compose_build_selected():
        _compose_mutation(DOCKER_COMPOSE_BUILD, "Compose Build")

    def compose_pull_selected():
        _compose_mutation(DOCKER_COMPOSE_PULL, "Compose Pull")

    def compose_stop_selected():
        _compose_mutation(DOCKER_COMPOSE_STOP, "Compose Stop")

    def compose_down_selected():
        _compose_mutation(DOCKER_COMPOSE_DOWN, "Compose Down")

    def compose_down_volumes_selected():
        _compose_mutation(
            DOCKER_COMPOSE_DOWN_VOLUMES, "Compose Down + Volumes",
            "Remove {projects} and delete its named volumes?\n\nData stored in those volumes is lost.")

    def compose_restart_selected():
        _compose_mutation(DOCKER_COMPOSE_RESTART, "Compose Restart")

    def compose_logs_selected():
        if not check_docker_running(): return
        rows = _selected_rows("compose project", table_type='compose', allow_multiple=False)
        if not rows:
            return
        project_name, files = _compose_project(rows[0])
        files_arg = _compose_files_to_args(files)
        if not files_arg:
            messagebox.showwarning("Missing Compose Files", "This project does not expose compose file paths.")
            return
        _run_output_command(
            DOCKER_COMPOSE_LOGS.format(files=files_arg, lines="200"),
            f"Compose Logs - {project_name}",
        )

    def compose_services_selected():
        if not check_docker_running(): return
        rows = _selected_rows("compose project", table_type='compose', allow_multiple=False)
        if not rows:
            return
        project_name, files = _compose_project(rows[0])
        files_arg = _compose_files_to_args(files)
        if not files_arg:
            messagebox.showwarning("Missing Compose Files", "This project does not expose compose file paths.")
            return

        def callback(result):
            import json as _json
            service_rows = []
            try:
                data = _json.loads(result.strip() or "[]")
                for item in data:
                    ports = item.get("Publishers") or item.get("Ports") or ""
                    if isinstance(ports, list):
                        ports = ", ".join(
                            f"{p.get('PublishedPort', '')}:{p.get('TargetPort', '')}/{p.get('Protocol', '')}"
                            for p in ports if p.get("PublishedPort")
                        )
                    service_rows.append([
                        item.get("ID", "")[:12],
                        item.get("Name", ""),
                        item.get("Service", ""),
                        item.get("State", ""),
                        str(ports),
                    ])
            except (_json.JSONDecodeError, TypeError):
                pass
            display_manager.show_table(
                ["CONTAINER ID", "NAME", "SERVICE", "STATE", "PORTS"],
                service_rows,
                'compose_service',
                f"Compose Services - {project_name}",
                False,
            )

        async_run(
            DOCKER_COMPOSE_PS.format(files=files_arg),
            callback,
            sudo=True,
            sudo_password=get_sudo_password(),
            loading_callback=show_loading_callback,
        )

    def compose_inspect_selected():
        if not check_docker_running(): return
        rows = _selected_rows("compose project", table_type='compose', allow_multiple=False)
        if not rows:
            return
        project_name, files = _compose_project(rows[0])
        files_arg = _compose_files_to_args(files)
        if not files_arg:
            messagebox.showwarning("Missing Compose Files", "This project does not expose compose file paths.")
            return
        _run_output_command(
            DOCKER_COMPOSE_CONFIG.format(files=files_arg),
            f"Compose Config - {project_name}",
        )

    action_label = ttk.Label(action_frame, text="Actions on selected:",
                            font=("JetBrains Mono", 9, "bold"))

    btn_start_container = ttk.Button(action_frame, text="▶ Start",
                                     style="success.Outline.TButton",
                                     command=start_selected_container)
    Tooltip(btn_start_container, ACTION_TOOLTIPS["start_container"])

    btn_stop_container = ttk.Button(action_frame, text="⏸ Stop",
                                    style="warning.Outline.TButton",
                                    command=stop_selected_container)
    Tooltip(btn_stop_container, ACTION_TOOLTIPS["stop_container"])

    btn_restart_container = ttk.Button(action_frame, text="↻ Restart",
                                       style="warning.Outline.TButton",
                                       command=restart_selected_container)
    Tooltip(btn_restart_container, ACTION_TOOLTIPS["restart_container"])

    btn_pause_container = ttk.Button(action_frame, text="⏸ Pause",
                                     style="secondary.Outline.TButton",
                                     command=pause_selected_container)
    Tooltip(btn_pause_container, ACTION_TOOLTIPS["pause_container"])

    btn_unpause_container = ttk.Button(action_frame, text="▶ Resume",
                                       style="success.Outline.TButton",
                                       command=unpause_selected_container)
    Tooltip(btn_unpause_container, ACTION_TOOLTIPS["unpause_container"])

    btn_delete_container = ttk.Button(action_frame, text="🗑 Delete",
                                      style="danger.Outline.TButton",
                                      command=delete_selected_container)
    Tooltip(btn_delete_container, ACTION_TOOLTIPS["delete_container"])

    btn_rename_container = ttk.Button(action_frame, text="✎ Rename",
                                      style="info.Outline.TButton",
                                      command=rename_selected_container)
    Tooltip(btn_rename_container, ACTION_TOOLTIPS["rename_container"])

    btn_container_terminal = ttk.Button(action_frame, text="💻 Terminal",
                                        style="info.Outline.TButton",
                                        command=lambda: _open_container_terminal(root, display_manager))
    Tooltip(btn_container_terminal, ACTION_TOOLTIPS["container_terminal"])

    btn_view_logs = ttk.Button(action_frame, text="📄 Logs",
                               style="secondary.Outline.TButton",
                               command=lambda: _view_container_logs(root, display_manager))
    Tooltip(btn_view_logs, ACTION_TOOLTIPS["view_logs"])

    btn_inspect_container = ttk.Button(action_frame, text="🔎 Inspect",
                                       style="secondary.Outline.TButton",
                                       command=inspect_selected_container)
    Tooltip(btn_inspect_container, ACTION_TOOLTIPS["inspect_container"])

    btn_commit_container = ttk.Button(action_frame, text="📦 Commit",
                                      style="secondary.Outline.TButton",
                                      command=commit_selected_container)
    Tooltip(btn_commit_container, ACTION_TOOLTIPS["commit_container"])

    btn_browse_files = ttk.Button(action_frame, text="📂 Files",
                                   style="info.Outline.TButton",
                                   command=lambda: _browse_container_files(root, display_manager))
    Tooltip(btn_browse_files, ACTION_TOOLTIPS["browse_files"])

    btn_delete_image = ttk.Button(action_frame, text="🗑 Delete Image",
                                  style="danger.Outline.TButton",
                                  command=delete_selected_image)
    Tooltip(btn_delete_image, ACTION_TOOLTIPS["delete_image"])

    btn_tag_image = ttk.Button(action_frame, text="🏷 Tag",
                               style="info.Outline.TButton",
                               command=tag_selected_image)
    Tooltip(btn_tag_image, ACTION_TOOLTIPS["tag_image"])

    btn_push_image = ttk.Button(action_frame, text="⬆ Push",
                                style="primary.Outline.TButton",
                                command=push_selected_image)
    Tooltip(btn_push_image, ACTION_TOOLTIPS["push_image"])

    btn_save_image = ttk.Button(action_frame, text="💾 Save",
                                style="secondary.Outline.TButton",
                                command=save_selected_image)
    Tooltip(btn_save_image, ACTION_TOOLTIPS["save_image"])

    btn_inspect_image = ttk.Button(action_frame, text="🔎 Inspect Image",
                                   style="secondary.Outline.TButton",
                                   command=inspect_selected_image)
    Tooltip(btn_inspect_image, ACTION_TOOLTIPS["inspect_image"])

    btn_history_image = ttk.Button(action_frame, text="🧱 History",
                                   style="secondary.Outline.TButton",
                                   command=history_selected_image)
    Tooltip(btn_history_image, ACTION_TOOLTIPS["history_image"])

    btn_delete_volume = ttk.Button(action_frame, text="🗑 Delete Volume",
                                   style="danger.Outline.TButton",
                                   command=delete_selected_volume)
    Tooltip(btn_delete_volume, ACTION_TOOLTIPS["delete_volume"])

    btn_inspect_volume = ttk.Button(action_frame, text="🔎 Inspect Volume",
                                    style="secondary.Outline.TButton",
                                    command=inspect_selected_volume)
    Tooltip(btn_inspect_volume, ACTION_TOOLTIPS["inspect_volume"])

    btn_run_container = ttk.Button(action_frame, text="▶ Run from Image",
                                   style="success.Outline.TButton",
                                   command=run_container_from_image)
    Tooltip(btn_run_container, ACTION_TOOLTIPS["run_container"])

    btn_stop_using = ttk.Button(action_frame, text="⏸ Stop Using Image",
                                style="warning.Outline.TButton",
                                command=stop_containers_using_image)
    Tooltip(btn_stop_using, ACTION_TOOLTIPS["stop_using_image"])

    btn_delete_network = ttk.Button(action_frame, text="🗑 Delete Network",
                                    style="danger.Outline.TButton",
                                    command=delete_selected_network)
    Tooltip(btn_delete_network, ACTION_TOOLTIPS["delete_network"])

    btn_inspect_network = ttk.Button(action_frame, text="🔎 Inspect Network",
                                     style="secondary.Outline.TButton",
                                     command=inspect_selected_network)
    Tooltip(btn_inspect_network, ACTION_TOOLTIPS["inspect_network"])

    btn_connect_network = ttk.Button(action_frame, text="🔌 Connect",
                                     style="info.Outline.TButton",
                                     command=connect_selected_network)
    Tooltip(btn_connect_network, ACTION_TOOLTIPS["connect_network"])

    btn_disconnect_network = ttk.Button(action_frame, text="⛔ Disconnect",
                                        style="warning.Outline.TButton",
                                        command=disconnect_selected_network)
    Tooltip(btn_disconnect_network, ACTION_TOOLTIPS["disconnect_network"])

    btn_compose_up = ttk.Button(action_frame, text="▶ Compose Up",
                                style="success.Outline.TButton",
                                command=compose_up_selected)
    Tooltip(btn_compose_up, ACTION_TOOLTIPS["compose_up"])

    btn_compose_up_build = ttk.Button(action_frame, text="🔨 Up --build",
                                      style="success.Outline.TButton",
                                      command=compose_up_build_selected)
    Tooltip(btn_compose_up_build, ACTION_TOOLTIPS["compose_up_build"])

    btn_compose_build = ttk.Button(action_frame, text="🏗 Compose Build",
                                   style="info.Outline.TButton",
                                   command=compose_build_selected)
    Tooltip(btn_compose_build, ACTION_TOOLTIPS["compose_build"])

    btn_compose_pull = ttk.Button(action_frame, text="⬇ Compose Pull",
                                  style="info.Outline.TButton",
                                  command=compose_pull_selected)
    Tooltip(btn_compose_pull, ACTION_TOOLTIPS["compose_pull"])

    btn_compose_stop = ttk.Button(action_frame, text="⏸ Compose Stop",
                                  style="warning.Outline.TButton",
                                  command=compose_stop_selected)
    Tooltip(btn_compose_stop, ACTION_TOOLTIPS["compose_stop"])

    btn_compose_down_volumes = ttk.Button(action_frame, text="🗑 Down + Volumes",
                                          style="danger.Outline.TButton",
                                          command=compose_down_volumes_selected)
    Tooltip(btn_compose_down_volumes, ACTION_TOOLTIPS["compose_down_volumes"])

    btn_compose_down = ttk.Button(action_frame, text="⏹ Compose Down",
                                  style="danger.Outline.TButton",
                                  command=compose_down_selected)
    Tooltip(btn_compose_down, ACTION_TOOLTIPS["compose_down"])

    btn_compose_restart = ttk.Button(action_frame, text="↻ Compose Restart",
                                     style="warning.Outline.TButton",
                                     command=compose_restart_selected)
    Tooltip(btn_compose_restart, ACTION_TOOLTIPS["compose_restart"])

    btn_compose_logs = ttk.Button(action_frame, text="📄 Compose Logs",
                                  style="secondary.Outline.TButton",
                                  command=compose_logs_selected)
    Tooltip(btn_compose_logs, ACTION_TOOLTIPS["compose_logs"])

    btn_compose_services = ttk.Button(action_frame, text="📋 Services",
                                      style="info.Outline.TButton",
                                      command=compose_services_selected)
    Tooltip(btn_compose_services, ACTION_TOOLTIPS["compose_services"])

    btn_compose_inspect = ttk.Button(action_frame, text="🔎 Compose Config",
                                     style="secondary.Outline.TButton",
                                     command=compose_inspect_selected)
    Tooltip(btn_compose_inspect, ACTION_TOOLTIPS["compose_inspect"])

    action_buttons = {
        'start': btn_start_container,
        'stop': btn_stop_container,
        'restart': btn_restart_container,
        'pause': btn_pause_container,
        'unpause': btn_unpause_container,
        'delete': btn_delete_container,
        'rename': btn_rename_container,
        'terminal': btn_container_terminal,
        'logs': btn_view_logs,
        'inspect_container': btn_inspect_container,
        'commit': btn_commit_container,
        'browse_files': btn_browse_files,
        'delete_image': btn_delete_image,
        'tag_image': btn_tag_image,
        'push_image': btn_push_image,
        'save_image': btn_save_image,
        'inspect_image': btn_inspect_image,
        'history_image': btn_history_image,
        'delete_volume': btn_delete_volume,
        'inspect_volume': btn_inspect_volume,
        'run': btn_run_container,
        'stop_using': btn_stop_using,
        'delete_network': btn_delete_network,
        'inspect_network': btn_inspect_network,
        'connect_network': btn_connect_network,
        'disconnect_network': btn_disconnect_network,
        'compose_up': btn_compose_up,
        'compose_up_build': btn_compose_up_build,
        'compose_build': btn_compose_build,
        'compose_pull': btn_compose_pull,
        'compose_stop': btn_compose_stop,
        'compose_down': btn_compose_down,
        'compose_down_volumes': btn_compose_down_volumes,
        'compose_restart': btn_compose_restart,
        'compose_logs': btn_compose_logs,
        'compose_services': btn_compose_services,
        'compose_inspect': btn_compose_inspect,
    }

    return action_buttons, action_label


def _open_container_terminal(root, display_manager):
    """Delegate to containers.dialogs to avoid circular imports."""
    from src.containers.dialogs import open_container_terminal_dialog
    open_container_terminal_dialog(root, display_manager)


def _view_container_logs(root, display_manager):
    """Delegate to containers.dialogs to avoid circular imports."""
    from src.containers.dialogs import view_container_logs_dialog
    view_container_logs_dialog(root, display_manager)


def _browse_container_files(root, display_manager):
    """Delegate to containers.dialogs to avoid circular imports."""
    from src.containers.dialogs import browse_container_files_dialog
    browse_container_files_dialog(root, display_manager)
