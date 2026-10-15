"""
Application help shown in the Help tab (rendered by src/help/help_view.py).

HELP_SECTIONS: (icon, title, one-line summary, blocks). A block is one of
  ("p", text)               paragraph
  ("steps", [text, ...])    numbered steps
  ("list", [text, ...])     bullets
  ("kv", [(term, text)])    term + explanation rows
  ("keys", [(keys, text)])  keyboard shortcuts, `keys` drawn as key caps ("Ctrl+A")
"""

HELP_SECTIONS = [
    ("🚀", "Getting started", "First launch in three steps", [
        ("steps", [
            "Launch the app and enter your sudo password once (not asked if your user is in the docker group). It is saved in the desktop keyring, or in ~/.docker-gui/config.json (readable only by you) when there is none.",
            "Check the Docker service status at the top of the sidebar (Running ✅ / Stopped ❌).",
            "Pick a category in the sidebar, then use the buttons above the output to list and manage resources.",
        ]),
    ]),
    ("🧭", "Sidebar categories", "What each category does", [
        ("kv", [
            ("🐳 Docker", "Start, stop or restart the Docker service, and clean everything up."),
            ("📦 Containers", "List all / running / stopped / paused containers; start, stop, restart or delete them in bulk."),
            ("🖼 Images", "List (all / used / unused / dangling), pull, log in to a registry, search Docker Hub, build, load, import, prune and delete images. Pull and Build keep running if you close their window."),
            ("💾 Volumes", "List all / used / unused volumes; create, prune or delete them."),
            ("🕸 Networks", "List networks; create or prune them."),
            ("🧩 Compose", "List Compose projects. “Up From File” takes compose files or a project folder and remembers it, so the project stays listed (as not running) after `compose down`."),
            ("📊 Stats", "Live CPU / memory / network / disk I/O per container (with CPU and memory trends and a refresh-interval button), plus Docker Disk Usage with Images, Containers, Volumes and Build Cache tabs."),
            ("⚙ System", "Docker version and info, contexts (switch between local and remote engines), a live events window, buildx builders and build-cache prune."),
            ("💻 Terminal", "A built-in shell for quick commands without leaving the app."),
        ]),
    ]),
    ("🖱", "Working with tables", "Select, search, sort and filter", [
        ("p", "Select one or more rows, then use the action buttons below the table. Right-click or double-click a row for the same actions and details."),
        ("kv", [
            ("Search", "Matches any column as you type. Esc clears it."),
            ("Sort", "Choose a column and Asc / Desc."),
            ("☰ Filters", "For tables with a date column: pick a Created preset or a custom From / To range (YYYY-MM-DD[ HH:MM], or Pick… for a calendar). Changes apply on Apply; Clear filters also empties the search box."),
            ("Copy", "Click a cell to outline it; Ctrl+C copies that cell, or the selected rows if no cell is active. The right-click menu has the same copy options."),
        ]),
    ]),
    ("🎯", "Row actions", "What you can do with a selected row", [
        ("kv", [
            ("Containers", "Start · Stop · Restart · Pause · Unpause · Rename · Delete · Terminal · Logs · Details · Processes · Changes · Inspect · Commit · Export"),
            ("Images", "Run · Tag · Save · Scan · Inspect · History · Stop Using · Delete"),
            ("Volumes", "Inspect · Delete"),
            ("Networks", "Connect · Disconnect · Inspect · Delete"),
            ("Compose", "Up · Down · Restart · Logs (with follow) · Services · Config"),
        ]),
        ("p", "Actions that change things keep the table on screen and report the result in the status bar; errors show the output with a “← Back” button."),
    ]),
    ("▶️", "Running an image", "The Run dialog", [
        ("p", "Select an image and click Run to start a container with:"),
        ("list", [
            "Container name",
            "Port mappings (host:container)",
            "Environment variables (KEY=value)",
            "Volume mounts (host_path:container_path)",
            "Network and restart policy (no / always / on-failure)",
        ]),
    ]),
    ("📜", "Logs & terminal", "Look inside a container", [
        ("kv", [
            ("Logs", "Select a container and click Logs. Turn on Follow to tail live; scroll up for earlier output."),
            ("Terminal", "Opens an interactive shell (bash/sh) inside the container in your system terminal (tilix, gnome-terminal, xfce4-terminal, konsole, mate-terminal, terminator or xterm)."),
        ]),
    ]),
    ("📋", "Commands tab", "Copy or download docker commands", [
        ("kv", [
            ("Used by this app", "Every command the app runs, exactly as it runs it (with its --format / --filter options), described by the button that uses it."),
            ("Reference", "Other common docker commands."),
        ]),
        ("list", [
            "Search the list, or narrow it with the category dropdown.",
            "Click a command (or its Copy button) to copy just that command. <placeholders> are for you to fill in.",
            "Compose commands are listed both ways: without -f (when you are in the project folder) and with -f <file.yml>.",
            "“Copy all” copies both sets; “Download” saves them as a .txt or .md file.",
        ]),
    ]),
    ("🎨", "Themes", "Change the look", [
        ("p", "Pick a theme from the dropdown at the bottom of the sidebar. It is remembered for next launch."),
        ("p", "Available: Darkly · Superhero · Solar · Vapor · Cosmo · Flatly"),
    ]),
    ("⌨️", "Keyboard shortcuts", "Faster navigation", [
        ("keys", [
            ("Tab", "Move focus to the next control (Shift+Tab goes back)"),
            ("Enter", "Activate the focused button"),
            ("Ctrl+→", "Move focus to the main toolbar"),
            ("Ctrl+←", "Move focus back to the sidebar"),
            ("Ctrl+C", "Copy the active cell, selected rows or selected text"),
            ("Ctrl+A", "Select all rows in a table"),
            ("Esc", "Clear the search box or close a menu"),
        ]),
    ]),
    ("🔑", "Password & security", "How your sudo password is handled", [
        ("kv", [
            ("Change", "Replace the stored sudo password."),
            ("Delete", "Remove it; you are asked again on the next launch."),
        ]),
        ("list", [
            "Stored in the desktop keyring when secret-tool is installed, otherwise in ~/.docker-gui/config.json with permissions 0600; never logged.",
            "If your user can run docker without sudo (docker group), no password is asked or stored.",
            "Registry passwords and tokens are sent to docker on stdin and never appear in a command line.",
            "Docker commands are built from fixed strings, so typed text cannot inject shell commands.",
        ]),
    ]),
    ("⚡", "Performance", "Why the app turns off input methods", [
        ("p", "The app disables X input-method support at start (XMODIFIERS=@im=none). With ibus, every widget made startup and screen changes take seconds. The only side effect is that ibus compose (e.g. CJK input) is unavailable inside this app."),
    ]),
]
