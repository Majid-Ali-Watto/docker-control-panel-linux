#!/usr/bin/env python3
"""
Docker GUI - Modular Version
A graphical user interface for managing Docker containers, images, and volumes.

This is the refactored main entry point following DRY and SOC patterns.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys

# Import configuration modules
from src.config.config_themes import themes
from src.help.help_commands import commands_info
from src.help.help_info import help_info
from src.config.config_menu import get_menu_structure

# Import utility modules
from src.utils.utils import check_docker_installed, is_docker_running
from src.config.config_manager import CONFIG_FILE
from src.ui.ui_components import (
    prompt_password_dialog, 
    prompt_docker_installation,
    change_password_dialog,
    delete_password_dialog
)
from src.ui.ui_display import DisplayManager
from src.ui.keyboard_navigation import (
    setup_keyboard_navigation,
    enable_button_enter_key,
    create_navigation_handlers,
    bind_global_navigation
)

# Import Docker action modules
from src.docker.docker_actions import (
    update_docker_status,
    start_docker_service,
    stop_docker_service,
    restart_docker_service,
    clean_all_resources,
    start_all_containers,
    stop_all_containers,
    restart_all_containers,
    delete_all_containers,
    delete_all_images,
    prune_volumes,
    delete_used_volumes,
    delete_all_volumes
)
from src.docker.docker_tables import (
    show_running_containers,
    show_all_containers,
    show_stopped_containers,
    show_containers_with_stats,
    show_images,
    show_unused_images,
    show_used_images,
    show_volumes,
    show_docker_disk_storage_simple
)

# Import dialogs and specific features
from src.docker.docker_gui_features import (
    pull_image_dialog,
    open_container_terminal_dialog,
    view_container_logs_dialog,
    docker_disk_usage_view,
    setup_table_context_menu,
    setup_text_context_menu,
    create_selected_item_actions
)


class DockerGUI:
    """Main Docker GUI Application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Docker Control Panel (Ubuntu)")
        
        # Setup window geometry
        # Update to ensure proper screen dimensions are retrieved
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Use more conservative sizing with bounds checking
        window_width = min(int(screen_width * 0.85), 1920)
        window_height = min(int(screen_height * 0.75), 1080)
        min_width = min(int(screen_width * 0.5), 800)
        min_height = min(int(screen_height * 0.4), 600)
        
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(min_width, min_height)
        
        # State variables
        self.docker_status_var = tk.StringVar()
        self.active_sidebar_button = None
        self.active_button = None
        self.sidebar_buttons = {}
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
        
        # Prompt for password
        if not prompt_password_dialog(self.root, None):
            messagebox.showerror("Error", "Sudo password is required to run this application")
            self.root.destroy()
            sys.exit(1)
        
        # Initialize status
        update_docker_status(self.root, self.docker_status_var)
        
        # Auto-select Docker category
        self.select_initial_category()
    
    def setup_styles(self):
        """Setup TTK styles"""
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.current_theme = "Default"
        
        # Configure active button style
        self.style.configure('Active.TButton', background='#0078d4', foreground='white')
        self.style.map('Active.TButton',
            background=[('active', '#0078d4'), ('!active', '#0078d4')],
            foreground=[('active', 'white'), ('!active', 'white')]
        )
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create sidebar
        self.create_sidebar(main_container)
        
        # Create main content area
        self.create_main_content(main_container)
    
    def create_sidebar(self, parent):
        """Create left sidebar with menu"""
        sidebar = ttk.Frame(parent, width=200, relief=tk.RIDGE, borderwidth=2)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0), pady=5)
        sidebar.pack_propagate(False)
        
        # Sidebar title
        ttk.Label(sidebar, text="Docker Control", font=("JetBrains Mono", 12, "bold")).pack(pady=10)
        
        # Theme selector
        self.create_theme_selector(sidebar)
        
        ttk.Separator(sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10, padx=5)
        
        # Menu structure
        menu_structure = get_menu_structure(
            lambda: start_docker_service(self.root, self.docker_status_var, 
                                        self.show_loading, self.display_manager.show_text_output),
            lambda: stop_docker_service(self.root, self.docker_status_var, 
                                       self.show_loading, self.display_manager.show_text_output),
            lambda: restart_docker_service(self.root, self.docker_status_var, 
                                          self.show_loading, self.display_manager.show_text_output),
            lambda: clean_all_resources(self.display_manager.show_text_output, self.root),
            lambda: show_all_containers(self.display_manager.show_table, self.show_loading),
            lambda: show_running_containers(self.display_manager.show_table, self.show_loading),
            lambda: show_stopped_containers(self.display_manager.show_table, self.show_loading),
            lambda: start_all_containers(self.display_manager.show_text_output),
            lambda: stop_all_containers(self.display_manager.show_text_output),
            lambda: restart_all_containers(self.display_manager.show_text_output),
            lambda: delete_all_containers(self.display_manager.show_text_output, self.root),
            lambda: show_images(self.display_manager.show_table, self.show_loading),
            lambda: show_used_images(self.display_manager.show_table, self.show_loading),
            lambda: show_unused_images(self.display_manager.show_table, self.show_loading),
            lambda: pull_image_dialog(self.root, lambda: show_images(self.display_manager.show_table, self.show_loading)),
            lambda: delete_all_images(self.display_manager.show_text_output, self.root),
            lambda: show_volumes(self.display_manager.show_table, self.show_loading),
            lambda: prune_volumes(self.display_manager.show_text_output, self.root),
            lambda: delete_used_volumes(self.display_manager.show_text_output, self.root),
            lambda: delete_all_volumes(self.display_manager.show_text_output, self.root),
            lambda: show_containers_with_stats(self.display_manager.show_table, self.show_loading, self.display_manager),
            lambda: docker_disk_usage_view(self.display_manager.output_container, self.show_loading),
            lambda: show_docker_disk_storage_simple(self.display_manager.show_table, self.show_loading)
        )
        
        self.menu_structure = menu_structure
        
        # Create sidebar menu buttons
        for category in menu_structure.keys():
            btn = ttk.Button(sidebar, text=category, 
                           command=self.make_sidebar_command(category), width=20)
            btn.pack(pady=5, padx=10)
            self.sidebar_buttons[category] = btn
        
        # Password management and status at bottom
        self.create_sidebar_bottom(sidebar)
    
    def create_theme_selector(self, parent):
        """Create theme selector"""
        theme_frame = ttk.Frame(parent)
        theme_frame.pack(pady=5, padx=10, fill=tk.X)
        
        ttk.Label(theme_frame, text="Theme:", font=("Arial", 9)).pack(anchor=tk.W, pady=(0, 2))
        
        self.theme_var = tk.StringVar(value="Default")
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var, 
                                   values=list(themes.keys()), state="readonly", width=17)
        theme_combo.pack(fill=tk.X)
        theme_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_theme(self.theme_var.get()))
    
    def create_sidebar_bottom(self, parent):
        """Create bottom section of sidebar with password and status"""
        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        # Password management
        password_frame = ttk.LabelFrame(bottom_frame, text="Password", padding=5)
        password_frame.pack(fill=tk.X, pady=(0, 10))
        
        password_status = ttk.Label(password_frame, 
                                    text="Saved" if CONFIG_FILE.exists() else "Not Saved", 
                                    font=("Arial", 8))
        password_status.pack(pady=2)
        
        ttk.Button(password_frame, text="Change", 
                  command=lambda: change_password_dialog(self.root), width=8).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(password_frame, text="Delete", 
                  command=delete_password_dialog, width=8).pack(side=tk.LEFT, padx=2, pady=2)
        
        # Relaunch app button
        ttk.Separator(bottom_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(10, 5))
        ttk.Button(bottom_frame, text="🔄 Relaunch App", 
                  command=self.relaunch_app, width=18).pack(fill=tk.X, pady=(0, 10))
        
        # Docker status
        ttk.Separator(bottom_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 10))
        status_label = ttk.Label(bottom_frame, textvariable=self.docker_status_var, 
                                font=("JetBrains Mono", 9, "bold"), wraplength=180)
        status_label.pack()
    
    def create_main_content(self, parent):
        """Create main content area"""
        main_frame = ttk.Frame(parent, padding=10)
        main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Buttons frame
        self.btn_frame = ttk.LabelFrame(main_frame, text="Select a category from sidebar", padding=10)
        self.btn_frame.pack(fill=tk.X, pady=5)
        
        # Loading indicator
        self.loading_label = ttk.Label(main_frame, text="", font=("JetBrains Mono", 10), foreground="orange")
        self.loading_label.pack(fill=tk.X, pady=2)
        
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
        
        # Setup action buttons
        self.setup_action_buttons(action_frame)
        
        # Setup context menus
        setup_text_context_menu(text_widget, self.root)
        setup_table_context_menu(table_widget, self.root)
    
    def create_help_panel(self, parent):
        """Create help panel with tabs"""
        help_panel = ttk.Frame(parent, width=300)
        help_panel.pack_propagate(False)
        
        help_notebook = ttk.Notebook(help_panel)
        help_notebook.pack(fill=tk.BOTH, expand=True)
        help_notebook.enable_traversal()
        
        # Commands tab
        commands_tab = ttk.Frame(help_notebook)
        help_notebook.add(commands_tab, text="Commands")
        commands_text = tk.Text(commands_tab, wrap=tk.WORD, font=("Arial", 9), 
                               bg="#f9f9f9", fg="#333333")
        commands_text.pack(fill=tk.BOTH, expand=True)
        commands_scroll = ttk.Scrollbar(commands_tab, orient=tk.VERTICAL, command=commands_text.yview)
        commands_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        commands_text.configure(yscrollcommand=commands_scroll.set)
        commands_text.insert("1.0", commands_info)
        commands_text.config(state=tk.DISABLED)
        
        # Help tab
        help_tab = ttk.Frame(help_notebook)
        help_notebook.add(help_tab, text="Help")
        help_text = tk.Text(help_tab, wrap=tk.WORD, font=("Arial", 9), 
                           bg="#f9f9f9", fg="#333333")
        help_text.pack(fill=tk.BOTH, expand=True)
        help_scroll = ttk.Scrollbar(help_tab, orient=tk.VERTICAL, command=help_text.yview)
        help_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        help_text.configure(yscrollcommand=help_scroll.set)
        help_text.insert("1.0", help_info)
        help_text.config(state=tk.DISABLED)
        
        return help_panel
    
    def create_text_widget(self, parent):
        """Create text output widget"""
        text_frame = ttk.Frame(parent)
        text_widget = tk.Text(text_frame, wrap=tk.NONE, font=("JetBrains Mono", 10))
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
            lambda: show_images(self.display_manager.show_table, self.show_loading)
        )
        self.display_manager.set_action_buttons(action_buttons, action_label)
    
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
    
    def show_loading(self, visible):
        """Show or hide loading indicator"""
        if visible:
            self.loading_label.config(text="⏳ Loading...")
        else:
            self.loading_label.config(text="")
    
    def apply_theme(self, theme_name):
        """Apply selected theme"""
        self.current_theme = theme_name
        theme = themes[theme_name]
        
        self.style.theme_use(theme["ttk_theme"])
        
        # Configure active button style
        self.style.configure('Active.TButton', background=theme["button_active"], 
                           foreground=theme["button_active_fg"])
        self.style.map('Active.TButton',
            background=[('active', theme["button_active"]), ('!active', theme["button_active"])],
            foreground=[('active', theme["button_active_fg"]), ('!active', theme["button_active_fg"])]
        )
        
        self.root.configure(bg=theme["bg"])
        self.display_manager.text_widget.configure(bg=theme["text_bg"], fg=theme["text_fg"], 
                                                   insertbackground=theme["text_fg"])
        
        # Reapply active styles
        if self.active_button:
            self.active_button.configure(style='Active.TButton')
        if self.active_sidebar_button:
            self.active_sidebar_button.configure(style='Active.TButton')
    
    def make_sidebar_command(self, category):
        """Create sidebar button command"""
        def wrapper():
            # Reset all sidebar button styles
            for btn in self.sidebar_buttons.values():
                btn.configure(style='TButton')
            
            # Highlight current sidebar button
            if category in self.sidebar_buttons:
                self.sidebar_buttons[category].configure(style='Active.TButton')
                self.active_sidebar_button = self.sidebar_buttons[category]
                self.active_sidebar_button_ref['button'] = self.active_sidebar_button
            
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
        self.active_button = None
        self.category_buttons = {}
        self.display_manager.update_action_buttons()
        
        # Show/hide help panel BEFORE creating buttons
        self.help_panel.pack_forget()
        if category == "Docker":
            self.help_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        # Update label
        self.btn_frame.config(text=f"{category} - Actions")
        
        # Show buttons
        buttons = self.menu_structure.get(category, [])
        max_cols = 7
        for i, (text, cmd) in enumerate(buttons):
            def make_command(command, btn_text):
                def wrapper():
                    # Reset all button styles
                    if self.active_button:
                        self.active_button.state(['!pressed'])
                        self.active_button.configure(style='TButton')
                    
                    # Highlight current button
                    btn = self.category_buttons.get(btn_text)
                    if btn:
                        btn.configure(style='Active.TButton')
                        self.active_button = btn
                    
                    # Execute command
                    if command:
                        command()
                return wrapper
            
            btn = ttk.Button(self.btn_frame, text=text, command=make_command(cmd, text))
            btn.grid(row=i // max_cols, column=i % max_cols, padx=5, pady=5, sticky="ew")
            self.category_buttons[text] = btn
            enable_button_enter_key(btn)
            
            # Execute first command automatically for non-Docker categories
            if i == 0 and cmd and category not in ["Docker"]:
                btn.configure(style='Active.TButton')
                self.active_button = btn
                cmd()
        
        for i in range(max_cols):
            self.btn_frame.columnconfigure(i, weight=1)
    
    def select_initial_category(self):
        """Select Docker category on startup"""
        if "Docker" in self.sidebar_buttons:
            self.sidebar_buttons["Docker"].configure(style='Active.TButton')
            self.active_sidebar_button = self.sidebar_buttons["Docker"]
            self.active_sidebar_button_ref['button'] = self.active_sidebar_button
        self.show_category_buttons("Docker")
        # Ensure help panel is visible for Docker category
        self.help_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
    
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
