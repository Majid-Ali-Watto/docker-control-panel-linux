#!/usr/bin/env python3
"""
Docker GUI - Modular Version
A graphical user interface for managing Docker containers, images, and volumes.

This is the refactored main entry point following DRY and SOC patterns.
"""

import sys
import os
import glob
import webbrowser

# Tk creates an X input-method context (XCreateIC) for many widgets, and with an XIM server
# such as ibus (XMODIFIERS=@im=ibus) every one is a ~90 ms round trip: ~11 s to first paint
# and slow screens. This panel needs no input-method composition, so opt out before Tk starts.
os.environ["XMODIFIERS"] = "@im=none"

# Prefer venv packages so ttkbootstrap uses the correct Pillow version
_venv_pkgs = glob.glob(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 '.venv', 'lib', 'python*', 'site-packages')
)
for _p in _venv_pkgs:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkbs

# Import configuration modules
from src.config.config_themes import themes, DEFAULT_THEME
from src.config.config_tooltips import (
    SIDEBAR_TOOLTIPS,
    CATEGORY_TOOLTIPS,
    SIDEBAR_BOTTOM_TOOLTIPS,
)
from src.help.commands_view import build_commands_tab
from src.help.help_creator import (
    APP_BUILT_WITH,
    APP_NAME,
    APP_REQUIRES,
    APP_TAGLINE,
    CREATOR_GITHUB_LABEL,
    CREATOR_GITHUB_URL,
    CREATOR_NAME,
    CREATOR_PORTFOLIO_LABEL,
    CREATOR_PORTFOLIO_URL,
    CREATOR_ROLE,
)
from src.help.help_info import help_info, docker_landing_info
from src.config.config_menu import get_menu_structure, VIEW_BUTTONS

# Import utility modules
from src.utils.utils import check_docker_installed, is_docker_running, check_terminal_installed
from src.config.config_manager import has_saved_password, load_selected_theme, save_selected_theme
from src.ui.ui_components import (
    prompt_password_dialog,
    prompt_docker_installation,
    change_password_dialog,
    delete_password_dialog,
    Tooltip,
)

from src.ui.ui_display import DisplayManager
from src.ui.terminal_panel import TerminalPanel
from src.ui.rounded import apply_rounded_styles, RoundedPanel, make, readable
from src.ui.keyboard_navigation import (
    setup_keyboard_navigation,
    enable_button_enter_key,
    create_navigation_handlers,
    bind_global_navigation
)

# Import Docker action modules
from src.docker.actions import (
    update_docker_status, start_docker_service, stop_docker_service,
    restart_docker_service, clean_all_resources,
)
from src.containers.actions import (
    start_all_containers, stop_all_containers, restart_all_containers, delete_all_containers,
)
from src.containers.tables import (
    show_running_containers, show_all_containers, show_stopped_containers, show_paused_containers,
)
from src.containers.dialogs import (
    open_container_terminal_dialog, view_container_logs_dialog,
)
from src.images.actions import delete_all_images, prune_images
from src.images.tables import show_images, show_unused_images, show_used_images
from src.images.dialogs import (
    pull_image_dialog, push_image_dialog, search_hub_dialog, build_image_dialog,
    reopen_latest_build_status_window, reopen_latest_pull_status_window, load_image_dialog,
)
from src.volumes.actions import prune_volumes, delete_used_volumes, delete_all_volumes
from src.volumes.tables import show_volumes, show_used_volumes, show_unused_volumes
from src.volumes.dialogs import create_volume_dialog
from src.networks.actions import prune_networks
from src.networks.tables import show_networks
from src.networks.dialogs import create_network_dialog
from src.compose.tables import show_compose_projects
from src.compose.dialogs import compose_up_from_file_dialog
from src.stats.tables import show_containers_with_stats, show_docker_disk_storage_simple
from src.stats.dialogs import docker_disk_usage_view
from src.shared.context_menus import setup_table_context_menu, setup_text_context_menu
from src.shared.item_actions import create_selected_item_actions


class DockerGUI:
    """Main Docker GUI Application"""
    
    def __init__(self):
        saved_theme = load_selected_theme()
        self.initial_theme = saved_theme if saved_theme in themes else DEFAULT_THEME

        self.root = ttkbs.Window(
            title="Docker Control Panel",
            themename=themes[self.initial_theme]["ttkbs_theme"]
        )
        
        # Setup window geometry
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.screen_width = screen_width

        window_width = min(int(screen_width * 0.85), 1920)
        window_height = min(int(screen_height * 0.75), 1080)
        min_width = int(screen_width * 0.6)
        min_height = min(int(screen_height * 0.4), 600)

        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(min_width, min_height)
        self._maximize()
        
        # References to manually themed widgets (updated on theme change)
        self.sidebar = None
        
        # State variables
        self.docker_status_var = tk.StringVar()
        self.active_sidebar_button = None
        self.active_button = None
        self.sidebar_buttons = {}
        self.sidebar_indicators = {}
        self.sidebar_row_frames = {}
        self.sidebar_icon_labels = {}
        self.active_category = None
        self.category_buttons = {}
        self.active_sidebar_button_ref = {'button': None}
        
        # Setup UI
        self.setup_styles()
        self.create_widgets()
        self.setup_keyboard_nav()
        
        # Check Docker installation
        if not check_docker_installed():
            prompt_docker_installation()
            messagebox.showinfo("Application Closed", "Please install Docker and restart the application.")
            self.root.destroy()
            sys.exit(0)

        # Check for a terminal emulator (needed for the Container Terminal feature)
        if not check_terminal_installed():
            proceed = messagebox.askyesno(
                "No Terminal Emulator Found",
                "The Container Terminal feature requires a terminal emulator,\n"
                "but none was found on your system.\n\n"
                "Install one with:\n"
                "    sudo apt install tilix\n\n"
                "Continue without terminal support?",
                icon="warning",
            )
            if not proceed:
                self.root.destroy()
                sys.exit(0)

        # Prompt for password
        if not prompt_password_dialog(self.root, None):
            messagebox.showerror("Error", "Sudo password is required to run this application")
            self.root.destroy()
            sys.exit(1)
        
        # Initialize status
        update_docker_status(self.root, self.docker_status_var)
        
        # Auto-select Docker category
        self.select_initial_category()
    
    def _maximize(self):
        """Open maximised (title bar kept); the geometry above is the restored size."""
        try:
            self.root.attributes("-zoomed", True)      # X11 / Wayland (Linux)
        except tk.TclError:
            self.root.state("zoomed")                  # Windows / macOS

    def setup_styles(self):
        """Setup TTK styles via ttkbootstrap"""
        self.style = ttkbs.Style()  # returns the singleton created by Window
        self.current_theme = self.initial_theme
        self._configure_treeview_grid(themes[self.current_theme])
        for style_name in (
            "TButton", "primary.TButton", "secondary.TButton", "success.TButton",
            "danger.TButton", "warning.TButton", "info.TButton",
            "primary.Outline.TButton", "secondary.Outline.TButton",
            "success.Outline.TButton", "danger.Outline.TButton",
            "warning.Outline.TButton", "info.Outline.TButton",
        ):
            self.style.configure(style_name, padding=(6, 2))
        apply_rounded_styles(self.style, self.root)
    
    def _configure_treeview_grid(self, theme):
        """Apply cell-border / grid-line styling to the Treeview widget."""
        border_color = theme.get("tree_border", "#555555")
        
        # fieldbackground is the "canvas" behind rows; row tags paint their own
        # background, so the 1–2 px gap between rows exposes this border color
        # → horizontal grid lines.
        self.style.configure(
            "Treeview",
            background=border_color,
            fieldbackground=border_color,
            rowheight=28,
            font=("JetBrains Mono", 9),
            borderwidth=1,
            relief="flat",
        )
        # Headings: groove relief gives a raised look that doubles as a vertical
        # column separator visible in the header band.
        self.style.configure(
            "Treeview.Heading",
            font=("Arial", 9, "bold"),
            relief="groove",
            borderwidth=1,
            padding=(6, 7),
        )
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Main container fills the whole window
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Create sidebar
        self.create_sidebar(main_container)

        # Create main content area
        self.create_main_content(main_container)
    
    def create_sidebar(self, parent):
        """Create left sidebar with menu"""
        theme = themes[self.current_theme]
        self.sidebar = tk.Frame(parent, width=210, bg=theme["sidebar_bg"])
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        sidebar = self.sidebar
        
        # App title in sidebar
        self.sidebar_title_label = tk.Label(
            sidebar, text="🐳 Docker Control Panel",
            bg=theme["sidebar_bg"], fg="#4ea8f7",
            font=("Arial", 10, "bold")
        )
        self.sidebar_title_label.pack(pady=(14, 2), padx=14, anchor=tk.W)

        # Docker status badge
        self.sidebar_status_label = tk.Label(
            sidebar,
            textvariable=self.docker_status_var,
            bg=theme["sidebar_bg"], fg="#888888",
            font=("Arial", 8),
        )
        self.sidebar_status_label.pack(padx=14, pady=(0, 6), anchor=tk.W)
        self._apply_sidebar_text_colors(theme)

        # Thin separator line
        tk.Frame(sidebar, bg="#333355", height=1).pack(fill=tk.X, padx=14, pady=(0, 8))
        
        # Menu structure
        menu_structure = get_menu_structure(
            lambda: start_docker_service(self.root, self.docker_status_var, 
                                        self.show_loading, self.display_manager.show_text_output),
            lambda: stop_docker_service(self.root, self.docker_status_var, 
                                       self.show_loading, self.display_manager.show_text_output),
            lambda: restart_docker_service(self.root, self.docker_status_var, 
                                          self.show_loading, self.display_manager.show_text_output),
            lambda: clean_all_resources(self.display_manager.show_text_output, self.root, self.show_loading),
            lambda: show_all_containers(self.display_manager.show_table, self.show_loading),
            lambda: show_running_containers(self.display_manager.show_table, self.show_loading),
            lambda: show_stopped_containers(self.display_manager.show_table, self.show_loading),
            lambda: show_paused_containers(self.display_manager.show_table, self.show_loading),
            lambda: start_all_containers(self.display_manager.show_text_output, self.show_loading),
            lambda: stop_all_containers(self.display_manager.show_text_output, self.show_loading),
            lambda: restart_all_containers(self.display_manager.show_text_output, self.show_loading),
            lambda: delete_all_containers(self.display_manager.show_text_output, self.root, self.show_loading),
            lambda: show_images(self.display_manager.show_table, self.show_loading),
            lambda: show_used_images(self.display_manager.show_table, self.show_loading),
            lambda: show_unused_images(self.display_manager.show_table, self.show_loading),
            lambda: pull_image_dialog(self.root, lambda: show_images(self.display_manager.show_table, self.show_loading)),
            lambda: search_hub_dialog(self.root, lambda: show_images(self.display_manager.show_table, self.show_loading), self.display_manager.show_text_output),
            lambda: reopen_latest_pull_status_window(self.root),
            lambda: build_image_dialog(
                self.root,
                self.display_manager.show_text_output,
                lambda: show_images(self.display_manager.show_table, self.show_loading),
            ),
            lambda: reopen_latest_build_status_window(self.root),
            lambda: load_image_dialog(
                self.root,
                self.display_manager.show_text_output,
                lambda: show_images(self.display_manager.show_table, self.show_loading),
            ),
            lambda: prune_images(self.display_manager.show_text_output, self.root, self.show_loading),
            lambda: delete_all_images(self.display_manager.show_text_output, self.root, self.show_loading),
            lambda: show_volumes(self.display_manager.show_table, self.show_loading),
            lambda: show_used_volumes(self.display_manager.show_table, self.show_loading),
            lambda: show_unused_volumes(self.display_manager.show_table, self.show_loading),
            lambda: create_volume_dialog(
                self.root,
                self.display_manager.show_text_output,
                lambda: show_volumes(self.display_manager.show_table, self.show_loading),
            ),
            lambda: prune_volumes(self.display_manager.show_text_output, self.root, self.show_loading),
            lambda: delete_used_volumes(self.display_manager.show_text_output, self.root, self.show_loading),
            lambda: delete_all_volumes(self.display_manager.show_text_output, self.root, self.show_loading),
            lambda: show_networks(self.display_manager.show_table, self.show_loading),
            lambda: create_network_dialog(
                self.root,
                self.display_manager.show_text_output,
                lambda: show_networks(self.display_manager.show_table, self.show_loading),
            ),
            lambda: prune_networks(self.display_manager.show_text_output, self.root, self.show_loading),
            lambda: show_compose_projects(self.display_manager.show_table, self.show_loading),
            lambda: compose_up_from_file_dialog(
                self.root,
                self.display_manager.show_text_output,
                lambda: show_compose_projects(self.display_manager.show_table, self.show_loading),
                self.show_loading,
            ),
            lambda: show_containers_with_stats(self.display_manager.show_table, self.show_loading, self.display_manager),
            lambda: docker_disk_usage_view(self.display_manager, self.show_loading),
            lambda: show_docker_disk_storage_simple(self.display_manager.show_table, self.show_loading)
        )
        
        self.menu_structure = menu_structure
        
        # Create sidebar menu buttons
        icons = {
            "Docker": "🐳",
            "Containers": "📦",
            "Images": "🖼",
            "Volumes": "💾",
            "Networks": "🕸",
            "Compose": "🧩",
            "Terminal": "🖥",
            "Stats": "📊",
        }
        theme = themes[self.current_theme]
        for category in menu_structure.keys():
            icon = icons.get(category, "•")

            # Row frame holds the accent indicator + the button side-by-side
            row_frame = tk.Frame(sidebar, bg=theme["sidebar_bg"])
            row_frame.pack(pady=2, padx=10, fill=tk.X)

            # Left accent strip — always present, color shows active state
            indicator = tk.Frame(row_frame, width=4, bg=theme["sidebar_bg"])
            indicator.pack(side=tk.LEFT, fill=tk.Y)

            # Fixed-width icon cell so all category labels start at the same X
            icon_cell = tk.Frame(row_frame, width=28, bg=theme["sidebar_bg"])
            icon_cell.pack(side=tk.LEFT, fill=tk.Y, padx=(4, 0))
            icon_cell.pack_propagate(False)
            icon_lbl = tk.Label(icon_cell, text=icon, font=("Arial", 11),
                                bg=theme["sidebar_bg"], fg=theme["text_fg"],
                                anchor="center")
            icon_lbl.pack(fill=tk.BOTH, expand=True)

            btn = ttk.Button(
                row_frame, text=f" {category}",
                command=self.make_sidebar_command(category),
            )
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # Forward icon clicks to the button
            cmd = self.make_sidebar_command(category)
            icon_cell.bind("<Button-1>", lambda e, c=cmd: c())
            icon_lbl.bind("<Button-1>", lambda e, c=cmd: c())

            self.sidebar_buttons[category] = btn
            self.sidebar_indicators[category] = indicator
            self.sidebar_row_frames[category] = row_frame
            self.sidebar_icon_labels[category] = icon_lbl
            if category in SIDEBAR_TOOLTIPS:
                Tooltip(btn, SIDEBAR_TOOLTIPS[category])
        
        # Separator before bottom area
        tk.Frame(sidebar, bg="#333355", height=1).pack(fill=tk.X, padx=14, pady=(12, 8))
        
        # Theme selector
        self.create_theme_selector(sidebar)
        
        # Password management and status at bottom
        self.create_sidebar_bottom(sidebar)
    
    def _apply_sidebar_text_colors(self, theme):
        """Title and status text keep their hue but are adjusted to be legible on this sidebar."""
        bg = theme["sidebar_bg"]
        self.sidebar_title_label.configure(fg=readable("#4ea8f7", bg))
        self.sidebar_status_label.configure(fg=readable("#888888", bg))

    def create_theme_selector(self, parent):
        """Create theme selector"""
        theme_frame = ttk.Frame(parent)
        theme_frame.pack(pady=5, padx=10, fill=tk.X)
        
        ttk.Label(theme_frame, text="🎨 Theme", font=("Arial", 9)).pack(anchor=tk.W, pady=(0, 4))
        
        self.theme_var = tk.StringVar(value=self.current_theme)
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var,
                                   values=list(themes.keys()), state="readonly", width=17)
        theme_combo.pack(fill=tk.X)
        theme_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_theme(self.theme_var.get()))
    
    def create_sidebar_bottom(self, parent):
        """Create bottom section of sidebar with password and status"""
        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        # Password management
        password_frame = ttk.LabelFrame(bottom_frame, text="🔑 Password", padding=5)
        password_frame.pack(fill=tk.X, pady=(0, 8))
        
        password_status = ttk.Label(
            password_frame,
            text="● Saved" if has_saved_password() else "○ Not Saved",
            font=("Arial", 8)
        )
        password_status.pack(pady=2)
        
        pw_btn_row = ttk.Frame(password_frame)
        pw_btn_row.pack()
        btn_change = ttk.Button(pw_btn_row, text="Change", style="secondary.TButton",
                                command=lambda: change_password_dialog(self.root), width=8)
        btn_change.pack(side=tk.LEFT, padx=2, pady=2)
        Tooltip(btn_change, SIDEBAR_BOTTOM_TOOLTIPS["change_password"])

        btn_del_pw = ttk.Button(pw_btn_row, text="Delete", style="danger.Outline.TButton",
                                command=delete_password_dialog, width=8)
        btn_del_pw.pack(side=tk.LEFT, padx=2, pady=2)
        Tooltip(btn_del_pw, SIDEBAR_BOTTOM_TOOLTIPS["delete_password"])

        # Relaunch app button
        btn_relaunch = ttk.Button(bottom_frame, text="🔄 Relaunch App", style="secondary.TButton",
                                  command=self.relaunch_app)
        btn_relaunch.pack(fill=tk.X, pady=(6, 0))
        Tooltip(btn_relaunch, SIDEBAR_BOTTOM_TOOLTIPS["relaunch_app"])
    
    def create_main_content(self, parent):
        """Create main content area"""
        main_frame = ttk.Frame(parent, padding=(10, 8, 10, 8))
        main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Action toolbar frame
        self.btn_frame = ttk.LabelFrame(main_frame, text="Select a category from the sidebar", padding=(10, 8))
        self.btn_frame.pack(fill=tk.X, pady=(0, 6))

        # Docker info panel (shown only when Docker category is active)
        self._docker_info_panel = self._create_docker_info_panel(main_frame)

        # Status bar: result of the last action (packed before the content so it stays visible)
        self.status_label = ttk.Label(main_frame, text="Ready", style="secondary.TLabel",
                                      font=("Arial", 9), anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(4, 0))

        # Content area with output and help
        content_area = ttk.Frame(main_frame)
        content_area.pack(fill=tk.BOTH, expand=True)
        
        # Help panel (create and pack first on the right side)
        self.help_panel = self.create_help_panel(content_area)
        # Don't pack it initially, let show_category_buttons control it
        
        # Output container (pack after help panel is created)
        output_container = ttk.Frame(content_area)
        output_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create display widgets
        text_frame, text_widget = self.create_text_widget(output_container)
        table_frame, table_widget, action_frame = self.create_table_widget(output_container)
        
        # Initialize display manager
        self.display_manager = DisplayManager(output_container, table_frame, text_frame,
                                              table_widget, text_widget, action_frame)

        # Terminal panel — lives inside output_container, shown only when Terminal is active
        self._terminal_panel = TerminalPanel(output_container)

        # Setup action buttons
        self.setup_action_buttons(action_frame)

        # Setup context menus
        setup_text_context_menu(text_widget, self.root)
        setup_table_context_menu(self.display_manager, self.root)
    
    def _create_docker_info_panel(self, parent):
        """Create app-description banner shown below the toolbar when Docker is active."""
        BG = "#0d1117"
        panel = RoundedPanel(parent, BG, radius=12, padding=2)
        body = panel.body

        # Left column: whale + title + tagline
        left = make(tk.Frame, body, bg=BG)
        left.pack(side=tk.LEFT, padx=(14, 24), pady=10)

        make(tk.Label, left, text="🐳  Docker Control Panel",
             font=("JetBrains Mono", 12, "bold"), bg=BG, fg="#4ea8f7").pack(anchor=tk.W)
        make(tk.Label, left, text="A graphical Docker manager for Linux",
             font=("Arial", 9), bg=BG, fg="#6e7f92").pack(anchor=tk.W, pady=(2, 0))

        # Vertical divider
        make(tk.Frame, body, bg="#1e2d3d", width=1).pack(side=tk.LEFT, fill=tk.Y, pady=6)

        # Centre column: feature chips
        centre = make(tk.Frame, body, bg=BG)
        centre.pack(side=tk.LEFT, padx=20, pady=10)

        make(tk.Label, centre, text="Features",
             font=("Arial", 8, "bold"), bg=BG, fg="#6e7f92").pack(anchor=tk.W)

        chips_row = make(tk.Frame, centre, bg=BG)
        chips_row.pack(anchor=tk.W, pady=(4, 0))

        _FEATURES = [
            ("📦 Containers", "#1a4a6b"),
            ("🖼 Images",      "#1a4a2b"),
            ("💾 Volumes",     "#4a3a1a"),
            ("🕸 Networks",    "#3a1a4a"),
            ("🧩 Compose",     "#1a3a4a"),
            ("📊 Stats",       "#4a1a1a"),
        ]
        for label, chip_bg in _FEATURES:
            make(tk.Label, chips_row, text=f" {label} ",
                 font=("Arial", 8, "bold"), bg=chip_bg, fg="#c0d8f0",
                 relief="flat", padx=4, pady=3).pack(side=tk.LEFT, padx=(0, 6))

        # Vertical divider
        make(tk.Frame, body, bg="#1e2d3d", width=1).pack(side=tk.LEFT, fill=tk.Y, pady=6)

        # Right column: quick tips
        right = make(tk.Frame, body, bg=BG)
        right.pack(side=tk.LEFT, padx=20, pady=10)

        make(tk.Label, right, text="Quick Tips",
             font=("Arial", 8, "bold"), bg=BG, fg="#6e7f92").pack(anchor=tk.W)

        _TIPS = [
            "• Click a sidebar category to explore Docker resources",
            "• Select a row in the table, then use the action buttons below",
            "• Right-click any table row for a context menu",
        ]
        for tip in _TIPS:
            make(tk.Label, right, text=tip, font=("Arial", 8), bg=BG, fg="#8a9fb5",
                 anchor=tk.W, justify=tk.LEFT).pack(anchor=tk.W, pady=1)

        # Panel starts hidden; show_category_buttons controls visibility
        return panel

    def create_help_panel(self, parent):
        """Create help panel with tabs"""
        theme = themes[self.current_theme]
        link_color = theme.get("link_fg", theme["text_fg"])
        help_panel_width = int(self.screen_width * 0.4)
        help_panel = ttk.Frame(parent, width=help_panel_width)
        help_panel.pack_propagate(False)
        
        help_notebook = ttk.Notebook(help_panel)
        help_notebook.pack(fill=tk.BOTH, expand=True)
        help_notebook.enable_traversal()

        # Creator tab
        creator_tab = ttk.Frame(help_notebook)
        help_notebook.add(creator_tab, text=" Creator ")
        creator_content = tk.Frame(
            creator_tab,
            bg=theme["text_bg"],
            padx=18,
            pady=16,
        )
        creator_content.pack(fill=tk.BOTH, expand=True)

        # App banner
        app_banner = tk.Label(
            creator_content,
            text=f"🐳  {APP_NAME}",
            font=("Arial", 13, "bold"),
            bg=theme["text_bg"],
            fg=theme["text_fg"],
            anchor="w",
        )
        app_banner.pack(fill=tk.X)

        app_desc = tk.Label(
            creator_content,
            text=APP_TAGLINE,
            font=("Arial", 9),
            bg=theme["text_bg"],
            fg=theme["text_fg"],
            anchor="w",
        )
        app_desc.pack(fill=tk.X, pady=(0, 16))

        # Divider
        tk.Frame(creator_content, bg=theme.get("tree_border", "#444"), height=1).pack(fill=tk.X, pady=(0, 14))

        # Creator heading
        creator_title = tk.Label(
            creator_content,
            text="ABOUT THE CREATOR",
            font=("Arial", 9, "bold"),
            bg=theme["text_bg"],
            fg=theme["text_fg"],
            anchor="w",
        )
        creator_title.pack(fill=tk.X, pady=(0, 8))

        creator_name = tk.Label(
            creator_content,
            text=CREATOR_NAME,
            font=("Arial", 12, "bold"),
            bg=theme["text_bg"],
            fg=theme["text_fg"],
            anchor="w",
        )
        creator_name.pack(fill=tk.X)

        creator_role = tk.Label(
            creator_content,
            text=CREATOR_ROLE,
            font=("Arial", 10),
            bg=theme["text_bg"],
            fg=theme["text_fg"],
            anchor="w",
        )
        creator_role.pack(fill=tk.X, pady=(2, 16))

        # Divider
        tk.Frame(creator_content, bg=theme.get("tree_border", "#444"), height=1).pack(fill=tk.X, pady=(0, 14))

        # Links heading
        links_heading = tk.Label(
            creator_content,
            text="LINKS",
            font=("Arial", 9, "bold"),
            bg=theme["text_bg"],
            fg=theme["text_fg"],
            anchor="w",
        )
        links_heading.pack(fill=tk.X, pady=(0, 6))

        portfolio_label = tk.Label(
            creator_content,
            text="🌐  Portfolio",
            font=("Arial", 10, "bold"),
            bg=theme["text_bg"],
            fg=theme["text_fg"],
            anchor="w",
        )
        portfolio_label.pack(fill=tk.X)

        portfolio_link = tk.Label(
            creator_content,
            text="  " + CREATOR_PORTFOLIO_LABEL,
            font=("JetBrains Mono", 9, "underline"),
            bg=theme["text_bg"],
            fg=link_color,
            anchor="w",
            cursor="hand2",
        )
        portfolio_link.pack(fill=tk.X, pady=(2, 12))
        portfolio_link.bind("<Button-1>", lambda _: self.open_external_link(CREATOR_PORTFOLIO_URL))

        github_label = tk.Label(
            creator_content,
            text="🐙  GitHub",
            font=("Arial", 10, "bold"),
            bg=theme["text_bg"],
            fg=theme["text_fg"],
            anchor="w",
        )
        github_label.pack(fill=tk.X)

        github_link = tk.Label(
            creator_content,
            text="  " + CREATOR_GITHUB_LABEL,
            font=("JetBrains Mono", 9, "underline"),
            bg=theme["text_bg"],
            fg=link_color,
            anchor="w",
            cursor="hand2",
        )
        github_link.pack(fill=tk.X, pady=(2, 0))
        github_link.bind("<Button-1>", lambda _: self.open_external_link(CREATOR_GITHUB_URL))

        # Divider
        tk.Frame(creator_content, bg=theme.get("tree_border", "#444"), height=1).pack(fill=tk.X, pady=(14, 14))

        about_heading = tk.Label(
            creator_content, text="ABOUT THE APP",
            font=("Arial", 9, "bold"),
            bg=theme["text_bg"], fg=theme["text_fg"], anchor="w",
        )
        about_heading.pack(fill=tk.X, pady=(0, 6))

        about_lines = [
            tk.Label(
                creator_content, text=line, font=("Arial", 9),
                bg=theme["text_bg"], fg=theme["text_fg"], anchor="w",
            )
            for line in (f"Built with  {APP_BUILT_WITH}", f"Requires  {APP_REQUIRES}")
        ]
        for label in about_lines:
            label.pack(fill=tk.X, pady=1)

        creator_note = tk.Label(
            creator_content,
            text="Click a link to open it in your browser.",
            font=("Arial", 8),
            bg=theme["text_bg"],
            fg=theme["text_fg"],
            anchor="w",
        )
        creator_note.pack(fill=tk.X, pady=(14, 0))

        self._creator_frame = creator_content
        self._creator_text_labels = [
            app_banner, app_desc,
            creator_title, creator_name, creator_role,
            links_heading, portfolio_label, github_label,
            about_heading, *about_lines,
            creator_note,
        ]
        self._creator_link_labels = [portfolio_link, github_link]
        
        # Commands tab (copyable / downloadable reference)
        self._help_cmd_text = build_commands_tab(help_notebook, theme)

        # Help tab
        help_tab = ttk.Frame(help_notebook)
        help_notebook.add(help_tab, text=" Help ")
        help_text = tk.Text(
            help_tab, wrap=tk.WORD,
            font=("JetBrains Mono", 9),
            bg=theme["text_bg"], fg=theme["text_fg"],
            relief=tk.FLAT, borderwidth=0, padx=8, pady=6
        )
        help_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        help_scroll = ttk.Scrollbar(help_tab, orient=tk.VERTICAL, command=help_text.yview)
        help_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        help_text.configure(yscrollcommand=help_scroll.set)
        help_text.insert("1.0", help_info)
        help_text.config(state=tk.DISABLED)
        self._help_text = help_text
        
        return help_panel

    def open_external_link(self, url):
        """Open an external link in the default browser."""
        try:
            webbrowser.open_new_tab(url)
        except Exception:
            messagebox.showerror("Open Link", f"Could not open link:\n{url}")
    
    def create_text_widget(self, parent):
        """Create text output widget"""
        theme = themes[self.current_theme]
        text_frame = ttk.Frame(parent)
        text_widget = tk.Text(
            text_frame, wrap=tk.NONE,
            font=("JetBrains Mono", 10),
            bg=theme["text_bg"], fg=theme["text_fg"],
            insertbackground=theme["text_fg"],
            relief=tk.FLAT, borderwidth=0, padx=8, pady=6
        )
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scroll_y = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=text_widget.xview)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        text_widget.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        return text_frame, text_widget
    
    def create_table_widget(self, parent):
        """Create table widget"""
        table_frame = ttk.Frame(parent)
        table_container = ttk.Frame(table_frame)
        table_container.pack(fill=tk.BOTH, expand=True)
        
        table_scroll_y = ttk.Scrollbar(table_container, orient=tk.VERTICAL)
        table_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        table_scroll_x = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL)
        table_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        table = ttk.Treeview(table_container, yscrollcommand=table_scroll_y.set, 
                            xscrollcommand=table_scroll_x.set)
        table.pack(fill=tk.BOTH, expand=True)
        table_scroll_y.config(command=table.yview)
        table_scroll_x.config(command=table.xview)
        
        # Action frame
        action_frame = ttk.Frame(table_frame)
        action_frame.pack(fill=tk.X, pady=5)
        
        return table_frame, table, action_frame
    
    def setup_action_buttons(self, action_frame):
        """Setup action buttons for selected items"""
        action_buttons, action_label = create_selected_item_actions(
            action_frame, self.root, self.display_manager,
            lambda: show_images(self.display_manager.show_table, self.show_loading),
            self.show_loading,
        )
        self.display_manager.set_action_buttons(action_buttons, action_label)
        self.display_manager.status_label = self.status_label
    
    def setup_keyboard_nav(self):
        """Setup keyboard navigation"""
        setup_keyboard_navigation(self.root)
        bind_global_navigation(self.root)
        
        # Create and bind navigation handlers
        move_to_main, move_to_sidebar = create_navigation_handlers(
            self.btn_frame, self.active_sidebar_button_ref
        )
        self.root.bind("<Control-Right>", move_to_main)
        self.root.bind("<Control-Left>", move_to_sidebar)
    
    _SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    def show_loading(self, visible):
        """Show or hide loading overlay (thread-safe: schedules UI work on main thread)."""
        if visible:
            self.root.after(0, self._show_loading_overlay)
        else:
            self.root.after(0, self._hide_loading_overlay)

    def _show_loading_overlay(self):
        if getattr(self, '_loading_active', False):
            return
        self._loading_active = True
        self._spinner_frame_idx = 0
        self._spinner_job = None

        overlay = RoundedPanel(
            self.display_manager.output_container, '#1c2333',
            radius=16, outline='#2f3b52', padding=2, fit_width=True,
        )
        overlay.place(relx=0.5, rely=0.5, anchor='center')

        self._spinner_lbl = make(
            tk.Label, overlay.body, text=self._SPINNER_FRAMES[0],
            font=('JetBrains Mono', 32), bg='#1c2333', fg='#4ea8f7'
        )
        self._spinner_lbl.pack(padx=40, pady=(20, 6))

        make(
            tk.Label, overlay.body, text='Loading…',
            font=('Arial', 11), bg='#1c2333', fg='#9ab0cc'
        ).pack(padx=40, pady=(0, 20))

        self._loading_overlay = overlay
        self._tick_spinner()

    def _tick_spinner(self):
        if not getattr(self, '_loading_active', False):
            return
        overlay = getattr(self, '_loading_overlay', None)
        if not overlay or not overlay.winfo_exists():
            return
        self._spinner_frame_idx = (self._spinner_frame_idx + 1) % len(self._SPINNER_FRAMES)
        self._spinner_lbl.config(text=self._SPINNER_FRAMES[self._spinner_frame_idx])
        self._spinner_job = self.root.after(100, self._tick_spinner)

    def _hide_loading_overlay(self):
        self._loading_active = False
        job = getattr(self, '_spinner_job', None)
        if job:
            self.root.after_cancel(job)
            self._spinner_job = None
        overlay = getattr(self, '_loading_overlay', None)
        if overlay and overlay.winfo_exists():
            overlay.destroy()
        self._loading_overlay = None
    
    def apply_theme(self, theme_name):
        """Apply selected ttkbootstrap theme"""
        if theme_name not in themes:
            theme_name = DEFAULT_THEME

        self.current_theme = theme_name
        theme = themes[theme_name]
        link_color = theme.get("link_fg", theme["text_fg"])
        self.theme_var.set(theme_name)
        
        # Switch ttkbootstrap theme (updates all ttk widgets automatically)
        self.style.theme_use(theme["ttkbs_theme"])
        
        # Update manually-coloured tk widgets
        self.root.configure(bg=theme["root_bg"])
        
        if self.sidebar and self.sidebar.winfo_exists():
            self.sidebar.configure(bg=theme["sidebar_bg"])
            for child in self.sidebar.winfo_children():
                if isinstance(child, tk.Frame):
                    child.configure(bg=theme["sidebar_bg"])
                elif isinstance(child, tk.Label):
                    child.configure(bg=theme["sidebar_bg"])

        # Repaint sidebar row frames, accent indicators, and icon labels for the new theme
        for cat in self.sidebar_buttons:
            if cat in self.sidebar_row_frames and self.sidebar_row_frames[cat].winfo_exists():
                self.sidebar_row_frames[cat].configure(bg=theme["sidebar_bg"])
            if cat in self.sidebar_indicators and self.sidebar_indicators[cat].winfo_exists():
                is_active = (cat == self.active_category)
                self.sidebar_indicators[cat].configure(
                    bg=theme["indicator_color"] if is_active else theme["sidebar_bg"]
                )
            if cat in self.sidebar_icon_labels and self.sidebar_icon_labels[cat].winfo_exists():
                self.sidebar_icon_labels[cat].configure(
                    bg=theme["sidebar_bg"], fg=theme["text_fg"]
                )
        if hasattr(self, 'sidebar_status_label') and self.sidebar_status_label.winfo_exists():
            self.sidebar_status_label.configure(bg=theme["sidebar_bg"])
            self.sidebar_title_label.configure(bg=theme["sidebar_bg"])
            self._apply_sidebar_text_colors(theme)
        
        self.display_manager.text_widget.configure(
            bg=theme["text_bg"], fg=theme["text_fg"],
            insertbackground=theme["text_fg"]
        )
        
        # Update help panel text widgets if they exist
        if hasattr(self, '_help_cmd_text') and self._help_cmd_text.winfo_exists():
            self._help_cmd_text.configure(bg=theme["text_bg"], fg=theme["text_fg"])
        if hasattr(self, '_help_text') and self._help_text.winfo_exists():
            self._help_text.configure(bg=theme["text_bg"], fg=theme["text_fg"])
        if hasattr(self, '_creator_frame') and self._creator_frame.winfo_exists():
            self._creator_frame.configure(bg=theme["text_bg"])
        if hasattr(self, '_creator_text_labels'):
            for label in self._creator_text_labels:
                if label.winfo_exists():
                    label.configure(bg=theme["text_bg"], fg=theme["text_fg"])
        if hasattr(self, '_creator_link_labels'):
            for label in self._creator_link_labels:
                if label.winfo_exists():
                    label.configure(bg=theme["text_bg"], fg=link_color)
        
        # Update treeview alternating rows
        tw = self.display_manager.table_widget
        tw.tag_configure('oddrow', background=theme["tree_odd"])
        tw.tag_configure('evenrow', background=theme["tree_even"])
        
        # Reapply cell-border / grid-line treeview styling for new theme
        self._configure_treeview_grid(theme)

        # Rounded corners belong to the theme's styles, so they are rebuilt for the new theme
        apply_rounded_styles(self.style, self.root)
        
        # Reapply active button highlights using the new theme's style
        if self.active_button and self.active_button.winfo_exists():
            self.active_button.configure(style=theme["active_style"])
        if self.active_sidebar_button and self.active_sidebar_button.winfo_exists():
            self.active_sidebar_button.configure(style=theme["active_style"])

        save_selected_theme(theme_name)
    
    def make_sidebar_command(self, category):
        """Create sidebar button command"""
        def wrapper():
            theme = themes[self.current_theme]
            # Reset all sidebar buttons and indicators
            for cat, btn in self.sidebar_buttons.items():
                btn.configure(style='TButton')
                if cat in self.sidebar_indicators:
                    self.sidebar_indicators[cat].configure(bg=theme["sidebar_bg"])

            # Highlight the selected button with fill style + left accent strip
            if category in self.sidebar_buttons:
                self.sidebar_buttons[category].configure(style=theme["active_style"])
                self.sidebar_indicators[category].configure(bg=theme["indicator_color"])
                self.active_sidebar_button = self.sidebar_buttons[category]
                self.active_sidebar_button_ref['button'] = self.active_sidebar_button
                self.active_category = category

            # Show category buttons
            self.show_category_buttons(category)
        return wrapper
    
    def show_category_buttons(self, category):
        """Show buttons for selected category"""
        # Cancel any running operations when switching categories
        self.display_manager.cancel_running_operations()
        
        # Clear current buttons
        for widget in self.btn_frame.winfo_children():
            widget.destroy()
        
        # Clear output area
        for widget in self.display_manager.output_container.winfo_children():
            widget.pack_forget()
        
        # Reset state
        self.display_manager.current_table_type = None
        self.display_manager.view_refresh = None
        self.display_manager.set_status("Ready")
        self.active_button = None
        self.category_buttons = {}
        self.display_manager.update_action_buttons()
        
        # Show/hide help panel BEFORE creating buttons
        self.help_panel.pack_forget()
        if category == "Docker":
            self.help_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))

        # Show/hide Docker info panel
        self._docker_info_panel.pack_forget()
        if category == "Docker":
            self._docker_info_panel.pack(fill=tk.X, pady=(0, 6))

        # Show/hide terminal panel
        self._terminal_panel.pack_forget()
        if category == "Terminal":
            self._terminal_panel.pack(fill=tk.BOTH, expand=True)
            self._terminal_panel.focus_input()
            self.btn_frame.config(text="Terminal — Shell")
            ttk.Button(
                self.btn_frame, text="🗑 Clear",
                style="secondary.TButton",
                command=self._terminal_panel.clear,
            ).grid(row=0, column=0, padx=2, pady=1)
            return

        # Update label
        self.btn_frame.config(text=f"{category} - Actions")

        # Show buttons
        buttons = self.menu_structure.get(category, [])
        # Semantic style map: keywords in button text → ttkbootstrap style
        _DANGER_WORDS = ("delete", "clean", "prune", "remove")
        _WARN_WORDS = ("stop",)
        _SUCCESS_WORDS = ("start", "run", "pull")

        max_cols = 12
        for i, (text, cmd) in enumerate(buttons):
            def make_command(command, btn_text):
                def wrapper():
                    # Reset all button styles
                    if self.active_button:
                        self.active_button.state(['!pressed'])
                        t_lower = self.active_button.cget('text').lower()
                        if any(w in t_lower for w in _DANGER_WORDS):
                            self.active_button.configure(style='danger.Outline.TButton')
                        elif any(w in t_lower for w in _WARN_WORDS):
                            self.active_button.configure(style='warning.Outline.TButton')
                        elif any(w in t_lower for w in _SUCCESS_WORDS):
                            self.active_button.configure(style='success.Outline.TButton')
                        else:
                            self.active_button.configure(style='TButton')
                    
                    # Highlight current button
                    btn = self.category_buttons.get(btn_text)
                    if btn:
                        btn.configure(style='primary.TButton')
                        self.active_button = btn
                    
                    # Remember list-switching buttons so row actions can reload the list
                    if btn_text in VIEW_BUTTONS.get(category, ()):
                        self.display_manager.view_refresh = command

                    # Execute command
                    if command:
                        command()
                return wrapper
            
            # Choose initial button style based on label text
            text_lower = text.lower()
            if any(w in text_lower for w in _DANGER_WORDS):
                init_style = 'danger.Outline.TButton'
            elif any(w in text_lower for w in _WARN_WORDS):
                init_style = 'warning.Outline.TButton'
            elif any(w in text_lower for w in _SUCCESS_WORDS):
                init_style = 'success.Outline.TButton'
            else:
                init_style = 'TButton'
            
            btn = ttk.Button(self.btn_frame, text=text, style=init_style,
                             command=make_command(cmd, text))
            btn.grid(row=i // max_cols, column=i % max_cols, padx=4, pady=1)
            self.category_buttons[text] = btn
            enable_button_enter_key(btn)
            tip_text = CATEGORY_TOOLTIPS.get(category, {}).get(text)
            if tip_text:
                Tooltip(btn, tip_text)
            
            # Execute first command automatically for non-Docker categories
            if i == 0 and cmd and category not in ["Docker"]:
                btn.configure(style='primary.TButton')
                self.active_button = btn
                if text in VIEW_BUTTONS.get(category, ()):
                    self.display_manager.view_refresh = cmd
                cmd()
        
        for i in range(max_cols):
            self.btn_frame.columnconfigure(i, weight=0)

        if category == "Docker":
            self.display_manager.show_text_output(docker_landing_info)
    
    def select_initial_category(self):
        """Select Docker category on startup"""
        if "Docker" in self.sidebar_buttons:
            theme = themes[self.current_theme]
            self.sidebar_buttons["Docker"].configure(style=theme["active_style"])
            if "Docker" in self.sidebar_indicators:
                self.sidebar_indicators["Docker"].configure(bg=theme["indicator_color"])
            self.active_sidebar_button = self.sidebar_buttons["Docker"]
            self.active_sidebar_button_ref['button'] = self.active_sidebar_button
            self.active_category = "Docker"
        self.show_category_buttons("Docker")
        # Ensure help panel is visible for Docker category
        self.help_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        # Apply initial theme colours to treeview
        theme = themes[self.current_theme]
        tw = self.display_manager.table_widget
        tw.tag_configure('oddrow', background=theme["tree_odd"])
        tw.tag_configure('evenrow', background=theme["tree_even"])
        self._configure_treeview_grid(theme)
    
    def relaunch_app(self):
        """Relaunch the application"""
        import os
        import subprocess
        
        # Get the path to the current script
        script_path = os.path.abspath(sys.argv[0])
        
        # Close the current window
        self.root.destroy()
        
        # Relaunch the application
        subprocess.Popen([sys.executable, script_path])
        sys.exit(0)
    
    def run(self):
        """Run the application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    app = DockerGUI()
    app.run()


if __name__ == "__main__":
    main()
