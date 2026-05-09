"""
UI Components Module
Reusable UI components and dialogs.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess


class Tooltip:
    """Lightweight hover tooltip for any Tkinter widget."""

    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._job = None
        self._tip = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._cancel, add="+")
        widget.bind("<ButtonPress>", self._cancel, add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self._job = self.widget.after(self.delay, self._show)

    def _cancel(self, _event=None):
        if self._job:
            self.widget.after_cancel(self._job)
            self._job = None
        if self._tip:
            self._tip.destroy()
            self._tip = None

    def _show(self):
        widget = self.widget
        try:
            x = widget.winfo_rootx() + widget.winfo_width() // 2
            y = widget.winfo_rooty() + widget.winfo_height() + 6
        except Exception:
            return

        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_attributes("-topmost", True)

        tk.Label(
            tip, text=self.text,
            bg="#1c2333", fg="#d0e8ff",
            font=("Arial", 9),
            relief="flat",
            padx=10, pady=6,
            wraplength=300, justify="left",
        ).pack()

        tip.update_idletasks()
        tip_w = tip.winfo_reqwidth()
        tip_h = tip.winfo_reqheight()
        screen_w = widget.winfo_screenwidth()
        screen_h = widget.winfo_screenheight()

        tx = max(4, min(x - tip_w // 2, screen_w - tip_w - 4))
        ty = (widget.winfo_rooty() - tip_h - 6) if (y + tip_h > screen_h - 8) else y

        tip.wm_geometry(f"+{tx}+{ty}")
        self._tip = tip


def prompt_password_dialog(root, on_success_callback):
    """Prompt user for sudo password with a dialog"""
    from src.config.config_manager import load_saved_password, save_password, set_sudo_password
    
    # Check if password is saved
    saved_password = load_saved_password()
    if saved_password:
        set_sudo_password(saved_password)
        return True
    
    # Create password dialog
    dialog = tk.Toplevel(root)
    dialog.title("Sudo Password Required")
    dialog.geometry("400x180")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()
    
    # Keep window on top
    dialog.attributes('-topmost', True)
    dialog.lift()
    dialog.focus_force()
    
    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
    y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    
    result = {'password': None, 'save': False, 'cancelled': False}
    
    ttk.Label(dialog, text="🔑  Enter your sudo password:", font=("Arial", 11, "bold")).pack(pady=(20, 6))
    
    password_var = tk.StringVar()
    password_entry = ttk.Entry(dialog, textvariable=password_var, show="*", font=("JetBrains Mono", 11), width=30)
    password_entry.pack(pady=5)
    password_entry.focus()
    
    save_var = tk.BooleanVar(value=False)
    save_check = ttk.Checkbutton(dialog, text="Remember password", variable=save_var)
    save_check.pack(pady=8)
    
    # Enable keyboard navigation in dialog
    password_entry.bind("<Tab>", lambda e: save_check.focus() or "break")
    save_check.bind("<Tab>", lambda e: dialog.focus() or "break")
    
    def on_ok():
        pwd = password_var.get()
        if pwd:
            result['password'] = pwd
            result['save'] = save_var.get()
            dialog.destroy()
        else:
            dialog.attributes('-topmost', False)
            messagebox.showwarning("Password Required", "Please enter a password", parent=dialog)
            dialog.attributes('-topmost', True)
    
    def on_cancel():
        result['cancelled'] = True
        dialog.destroy()
    
    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=10)
    ttk.Button(btn_frame, text="Unlock", style="primary.TButton",
               command=on_ok, width=10).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Cancel", style="secondary.Outline.TButton",
               command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)
    
    password_entry.bind("<Return>", lambda e: on_ok())
    password_entry.bind("<Escape>", lambda e: on_cancel())
    
    dialog.wait_window()
    
    if result['cancelled'] or not result['password']:
        return False
    
    set_sudo_password(result['password'])
    
    if result['save']:
        save_password(result['password'])
    
    return True


def prompt_docker_installation():
    """Show error and prompt for Docker installation"""
    response = messagebox.askyesno(
        "Docker Not Found",
        "Docker is not installed on your system.\n\nWould you like to install Docker?",
        icon='error'
    )
    
    if response:
        # Open terminal with Docker installation commands
        # Detect the terminal emulator
        terminal_commands = [
            "gnome-terminal",
            "konsole",
            "xfce4-terminal",
            "xterm",
            "terminator",
            "tilix"
        ]
        
        # Installation commands for Ubuntu/Debian
        install_commands = (
            "echo 'Installing Docker...'; "
            "sudo apt-get update && "
            "sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common && "
            "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add - && "
            "sudo add-apt-repository 'deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable' && "
            "sudo apt-get update && "
            "sudo apt-get install -y docker-ce docker-ce-cli containerd.io && "
            "sudo systemctl start docker && "
            "sudo systemctl enable docker && "
            "echo 'Docker installation complete! Please restart this application.'; "
            "exec bash"
        )
        
        terminal_found = False
        for terminal in terminal_commands:
            try:
                # Check if terminal exists
                check_result = subprocess.run(
                    ["which", terminal],
                    capture_output=True
                )
                if check_result.returncode == 0:
                    # Open terminal with installation commands
                    if terminal == "gnome-terminal":
                        subprocess.Popen([terminal, "--", "bash", "-c", install_commands])
                    elif terminal == "konsole":
                        subprocess.Popen([terminal, "-e", "bash", "-c", install_commands])
                    elif terminal in ["xfce4-terminal", "terminator", "tilix"]:
                        subprocess.Popen([terminal, "-e", f"bash -c '{install_commands}'"])
                    else:  # xterm or fallback
                        subprocess.Popen([terminal, "-e", f"bash -c '{install_commands}'"])
                    terminal_found = True
                    break
            except:
                continue
        
        if not terminal_found:
            messagebox.showwarning(
                "Terminal Not Found",
                "Could not find a terminal emulator.\n\n"
                "Please install Docker manually using:\n\n"
                "sudo apt-get update\n"
                "sudo apt-get install docker.io\n"
                "sudo systemctl start docker\n"
                "sudo systemctl enable docker"
            )
    
    return False


def change_password_dialog(root):
    """Change sudo password dialog"""
    from src.config.config_manager import (
        save_password,
        delete_saved_password,
        set_sudo_password,
        has_saved_password,
    )
    
    dialog = tk.Toplevel(root)
    dialog.title("Change Password")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()

    ttk.Label(dialog, text="Enter new sudo password:", font=("Arial", 10)).pack(pady=(20, 6), padx=24)

    password_var = tk.StringVar()
    password_entry = ttk.Entry(dialog, textvariable=password_var, show="*", font=("Arial", 10), width=30)
    password_entry.pack(pady=5, padx=24)
    password_entry.focus()

    save_var = tk.BooleanVar(value=has_saved_password())
    save_check = ttk.Checkbutton(dialog, text="Remember password", variable=save_var)
    save_check.pack(pady=10)

    def on_ok():
        pwd = password_var.get()
        if pwd:
            set_sudo_password(pwd)
            if save_var.get():
                save_password(pwd)
            else:
                delete_saved_password()
            messagebox.showinfo("Success", "Password updated successfully", parent=dialog)
            dialog.destroy()
        else:
            messagebox.showwarning("Password Required", "Please enter a password", parent=dialog)

    from src.ui.keyboard_navigation import enable_button_enter_key

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=(4, 20))
    update_btn = ttk.Button(btn_frame, text="Update", style="primary.TButton", command=on_ok, width=12)
    update_btn.pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Cancel", style="secondary.Outline.TButton",
               command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)

    # Auto-size to fit all widgets, then center
    dialog.update_idletasks()
    w = max(dialog.winfo_reqwidth() + 20, 360)
    h = dialog.winfo_reqheight() + 16
    x = (dialog.winfo_screenwidth() - w) // 2
    y = (dialog.winfo_screenheight() - h) // 2
    dialog.geometry(f"{w}x{h}+{x}+{y}")

    password_entry.bind("<Return>", lambda e: on_ok())
    password_entry.bind("<Escape>", lambda e: dialog.destroy())
    password_entry.bind("<Tab>", lambda e: save_check.focus() or "break")
    save_check.bind("<Tab>", lambda e: update_btn.focus() or "break")
    enable_button_enter_key(update_btn)


def delete_password_dialog():
    """Delete saved password dialog"""
    from src.config.config_manager import delete_saved_password
    
    if messagebox.askyesno("Confirm", "Delete saved password?"):
        delete_saved_password()
        messagebox.showinfo("Success", "Saved password deleted")


def confirm_action_dialog(parent, title, message):
    """
    Custom confirmation dialog with NO button as default (focused).
    Returns True if user clicks Yes, False otherwise.
    """
    # Handle None parent - use root window
    if parent is None:
        parent = tk._default_root
    
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    
    # Make dialog modal and on top
    if parent:
        dialog.transient(parent)
    dialog.grab_set()
    dialog.attributes('-topmost', True)
    dialog.lift()
    dialog.focus_force()
    
    result = {'confirmed': False}
    
    # Message with better formatting
    msg_frame = ttk.Frame(dialog)
    msg_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(20, 10))
    
    msg_label = ttk.Label(msg_frame, text=message, font=("Arial", 11), 
                         wraplength=400, justify=tk.LEFT)
    msg_label.pack()
    
    # Buttons
    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=(10, 20))
    
    def on_yes():
        result['confirmed'] = True
        dialog.destroy()
    
    def on_no():
        result['confirmed'] = False
        dialog.destroy()
    
    yes_btn = ttk.Button(btn_frame, text="Yes", command=on_yes, width=12)
    yes_btn.pack(side=tk.LEFT, padx=10)
    
    no_btn = ttk.Button(btn_frame, text="No", command=on_no, width=12)
    no_btn.pack(side=tk.LEFT, padx=10)
    
    # Update and calculate required size
    dialog.update_idletasks()
    
    # Get the required width (minimum 400, maximum 500)
    dialog_width = max(400, min(500, msg_label.winfo_reqwidth() + 60))
    
    # Get required height based on content
    dialog_height = msg_label.winfo_reqheight() + btn_frame.winfo_reqheight() + 80
    
    # Set size and position
    dialog.geometry(f"{dialog_width}x{dialog_height}")
    dialog.resizable(False, False)
    
    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
    y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    
    # Set focus to NO button by default after a small delay
    dialog.after(100, lambda: no_btn.focus_set())
    
    # Bind keys
    yes_btn.bind("<Return>", lambda e: on_yes())
    no_btn.bind("<Return>", lambda e: on_no())
    dialog.bind("<Escape>", lambda e: on_no())
    
    # Enable keyboard navigation
    from src.ui.keyboard_navigation import enable_button_enter_key
    enable_button_enter_key(yes_btn)
    enable_button_enter_key(no_btn)
    
    # Ensure dialog stays on top
    dialog.after(10, lambda: dialog.lift())
    
    dialog.wait_window()
    
    return result['confirmed']


def create_table_widget(parent, columns):
    """Create a standardized table widget with scrollbars"""
    frame = ttk.Frame(parent)
    frame.pack(fill=tk.BOTH, expand=True)

    tree = ttk.Treeview(frame, columns=columns, show="headings")
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    tree.pack(fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    hsb.pack(side=tk.BOTTOM, fill=tk.X)

    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=150, anchor=tk.W)

    return tree
