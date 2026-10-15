"""
Application help text shown in the Help tab.
"""

help_info = """
╔══════════════════════════════════════════════════╗
║       DOCKER CONTROL PANEL — HELP GUIDE          ║
╚══════════════════════════════════════════════════╝

── GETTING STARTED ──────────────────────────────────

  1. Launch the app and enter your sudo password
     (stored securely in ~/.docker-gui/config.json
     with 0600 permissions — only you can read it).
  2. The sidebar shows the Docker service status
     (Running ✅ or Stopped ❌) at the top.
  3. Click a sidebar category to explore resources.

── SIDEBAR CATEGORIES ───────────────────────────────

  🐳 Docker
    Control the Docker service and perform bulk
    cleanup. The info panel below the toolbar
    shows app features and quick tips.

  📦 Containers
    View all, running, stopped, or paused
    containers. Perform bulk start/stop/restart/
    delete across all containers.

  🖼 Images
    View all, used, or unused images. Pull from
    Docker Hub, build from Dockerfile, load from
    archive, prune dangling layers, or delete all.
    Use Search Hub to find images with size info.

  💾 Volumes
    View all, used, or unused volumes. Create new
    volumes or prune unused ones.

  🕸 Networks
    View all networks. Create new networks or prune
    unused ones.

  🧩 Compose
    View Compose projects. "Up From File" takes one
    or more compose files or a project folder and
    remembers it, so the project stays listed (as
    not running) after `compose down`.

  📊 Stats
    Live container resource usage (CPU, memory,
    network I/O, block I/O). Docker Disk Usage has
    Images / Containers / Volumes / Build Cache tabs
    with the same search, sort and row actions.

  💻 Terminal
    Built-in terminal panel for quick commands
    without leaving the app.

── TABLE ACTIONS ────────────────────────────────────

  Select one or more rows in any table, then use
  the action buttons that appear below the table.

  Containers:
    Start · Stop · Restart · Pause · Unpause
    Rename · Delete · Terminal · Logs
    Inspect · Commit

  Images:
    Run · Tag · Save · Inspect · History
    Stop Using · Delete

  Volumes:
    Inspect · Delete

  Networks:
    Connect · Disconnect · Inspect · Delete

  Compose projects:
    Up · Down · Restart · Logs · Services · Config

  Right-click a row, or double-click it, for the
  same actions and details.

── PULL & BUILD STATUS ──────────────────────────────

  When a pull or build is started, a streaming log
  window opens. You can close it at any time — the
  operation keeps running in the background.

  To reopen the progress window after closing:
    Images → Pull Status  (for docker pull)
    Images → Build Status (for docker build)

── SEARCH, SORT & FILTER ────────────────────────────

  Above every table: a search box (matches any
  column, live), a sort dropdown with Asc/Desc, and
  a ☰ Filters button for tables with a date column.

  Filters → Created: pick a preset or "Custom range"
  and type From/To as YYYY-MM-DD[ HH:MM] (or use
  Pick… for a calendar). Changes apply on Apply;
  Clear filters also empties the search box.
  Esc clears the search box.

── CELLS, ROWS & CONTEXT MENU ───────────────────────

  Click a cell to outline it; Ctrl-C copies that
  cell, or the selected rows when no cell is active.
  Ctrl-A selects all rows. Double-click a row to open
  its details.

  Right-click a table for a menu: copy cell, copy
  rows, select all rows and the toolbar's row
  actions. Right-click a text area to copy text.

── CONTAINER TERMINAL ───────────────────────────────

  Select a container and click Terminal. A system
  terminal emulator will open with an interactive
  shell (bash/sh) inside that container.

  Supported emulators (auto-detected):
    tilix, gnome-terminal, xfce4-terminal,
    konsole, mate-terminal, terminator, xterm

── CONTAINER LOGS ───────────────────────────────────

  Select a container and click Logs to open the
  log viewer. Use the Follow toggle to tail logs
  live. Scroll up to review earlier output.

── IMAGE RUN DIALOG ─────────────────────────────────

  Select an image and click Run to launch a
  container with full options:
  • Container name
  • Port mappings  (host:container)
  • Environment variables  (KEY=value)
  • Volume mounts  (host_path:container_path)
  • Network selection
  • Restart policy  (no / always / on-failure)

── THEMES ───────────────────────────────────────────

  Choose a theme from the dropdown at the bottom
  of the sidebar. Your selection is persisted and
  restored on next launch.

  Available themes:
    Darkly · Superhero · Solar · Vapor
    Cosmo · Flatly

── PASSWORD MANAGEMENT ──────────────────────────────

  Change  — update the stored sudo password
  Delete  — remove the saved password (you will
             be prompted again on next launch)

── KEYBOARD SHORTCUTS ───────────────────────────────

  Tab / Shift-Tab   Move focus between controls
  Enter / Space     Activate focused button
  Ctrl →            Move focus to the main toolbar
  Ctrl ←            Move focus back to the sidebar
  Ctrl-C            Copy cell / rows / selected text
  Ctrl-A            Select all rows in a table
  Esc               Clear search · close a menu

── COMMANDS TAB ─────────────────────────────────────

  The Commands tab lists the docker commands used
  by this app and other common ones.
  • Click a command to copy it
  • Copy all / Copy selection copy to the clipboard
  • Download saves the whole reference as a file

── DISK USAGE VIEW ──────────────────────────────────

  Stats → Docker Disk Usage shows a detailed
  breakdown: image layers, container filesystems,
  and volumes — matching `docker system df -v`.

── SECURITY NOTES ───────────────────────────────────

  • Sudo password is stored at:
      ~/.docker-gui/config.json  (chmod 0600)
  • Only the current user can read the file.
  • The password is never logged or printed.
  • All docker commands use fixed constant strings
    — user input is never interpolated into shell
    commands, preventing injection attacks.

── PERFORMANCE ──────────────────────────────────────

  The app turns off X input-method support at start
  (XMODIFIERS=@im=none): with ibus every widget
  made startup and screen changes take seconds.

"""

# Shown in the output area of the Docker page until an action is run
docker_landing_info = """
  DOCKER SERVICE

  Start      Start docker.socket and docker.service
  Stop       Stop the Docker service and its socket
  Restart    Restart the Docker service
  Clean All  Stop and delete every container, image
             and volume (asks for confirmation)

  The service status is shown at the top of the sidebar.

  GETTING AROUND

  • Pick Containers, Images, Volumes, Networks, Compose
    or Stats in the sidebar to list and manage them.
  • Select rows, then use the action buttons below the table.
  • The Commands tab on the right lists docker commands
    you can click to copy or download.
"""
