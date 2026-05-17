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
    View active Compose projects. Start a project
    from a docker-compose.yml file.

  📊 Stats
    Live container resource usage (CPU, memory,
    network I/O, block I/O). Also view detailed
    Docker disk usage.

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

── PULL & BUILD STATUS ──────────────────────────────

  When a pull or build is started, a streaming log
  window opens. You can close it at any time — the
  operation keeps running in the background.

  To reopen the progress window after closing:
    Images → Pull Status  (for docker pull)
    Images → Build Status (for docker build)

── SEARCH & FILTER ──────────────────────────────────

  A search bar appears above every table. Type any
  keyword to filter rows across all visible columns
  in real time. Clear the field to restore all rows.

── CONTEXT MENU ─────────────────────────────────────

  Right-click any table row or text area for a
  context menu with copy options:
  • Copy a specific cell value
  • Copy the entire row as text

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
  Ctrl-C            Copy selected text (text areas)

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
"""
