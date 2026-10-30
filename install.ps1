# Docker Control Panel - Windows installer
#
# One command, no questions:   powershell -ExecutionPolicy Bypass -File install.ps1   (or double-click install.bat)
#
# Installs what is missing through winget (Python 3.12 with Tk, Docker Desktop), builds a private
# .venv with the Python dependencies, and adds a Start Menu shortcut plus a `docker-gui` command.
# Safe to run again. ASCII only on purpose: Windows PowerShell 5.1 misreads UTF-8 without a BOM.

$ErrorActionPreference = 'Continue'   # native commands are checked through $LASTEXITCODE instead

function Ok($text)   { Write-Host "  [ok] $text" -ForegroundColor Green }
function Warn($text) { Write-Host "  [!]  $text" -ForegroundColor Yellow }
function Info($text) { Write-Host "  ->   $text" -ForegroundColor Cyan }
function Step($text) { Write-Host ""; Write-Host $text -ForegroundColor Blue }
function Die($text)  { Write-Host "  [x]  $text" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "  Docker Control Panel - Installer" -ForegroundColor Cyan
Write-Host "  A graphical Docker manager for Linux, macOS and Windows"

$Root = $PSScriptRoot
$Venv = Join-Path $Root '.venv'
$VenvPython = Join-Path $Venv 'Scripts\python.exe'
$VenvPythonW = Join-Path $Venv 'Scripts\pythonw.exe'
$Winget = Get-Command winget -ErrorAction SilentlyContinue

# A Python this app can run on: 3.10+, with venv and a Tk of at least 8.6
function Test-Python($Exe, $Prefix) {
    try {
        & $Exe @Prefix -c "import sys, tkinter, venv, ensurepip; sys.exit(int(sys.version_info < (3, 10) or tkinter.TkVersion < 8.6))" *> $null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Find-Python {
    $candidates = @(@{ Exe = 'py'; Prefix = @('-3') }, @{ Exe = 'python'; Prefix = @() })
    $dirs = @("$env:LOCALAPPDATA\Programs\Python\Python3*", "$env:ProgramFiles\Python3*")
    foreach ($dir in $dirs) {
        Get-ChildItem -Path $dir -Filter python.exe -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            ForEach-Object { $candidates += @{ Exe = $_.FullName; Prefix = @() } }
    }
    foreach ($c in $candidates) {
        $cmd = Get-Command $c.Exe -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        if ($cmd.Source -like '*\WindowsApps\*') { continue }   # the Microsoft Store stub, not a real Python
        if (Test-Python $c.Exe $c.Prefix) { return $c }
    }
    return $null
}

# ---------------------------------------------------------------------------
Step "  [1/5]  Checking Windows"
# ---------------------------------------------------------------------------
if (-not $IsWindows -and $PSVersionTable.PSVersion.Major -ge 6) { Die "This installer is for Windows. On Linux / macOS run ./install.sh" }
Ok ("Windows " + [Environment]::OSVersion.Version)
if ($Winget) { Ok "winget found" } else { Warn "winget not found - missing programs will have to be installed by hand" }

# ---------------------------------------------------------------------------
Step "  [2/5]  Installing Python and Docker Desktop"
# ---------------------------------------------------------------------------
$py = Find-Python
if (-not $py) {
    if (-not $Winget) { Die "Python 3.10+ with Tk is required. Install it from https://www.python.org/downloads/ (keep 'tcl/tk' ticked) and run this again." }
    Info "Installing Python 3.12 with winget"
    winget install -e --id Python.Python.3.12 --scope user --silent --accept-source-agreements --accept-package-agreements
    $py = Find-Python
    if (-not $py) { Die "Python was installed but could not be found. Open a new terminal and run this script again." }
}
$pyVersion = & $py.Exe @($py.Prefix) --version
Ok "Python  ($pyVersion)"

$dockerExe = Get-Command docker -ErrorAction SilentlyContinue
$desktopExe = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
if ($dockerExe -or (Test-Path $desktopExe)) {
    Ok "Docker Desktop found"
} elseif ($Winget) {
    Info "Installing Docker Desktop with winget (accept the administrator prompt)"
    winget install -e --id Docker.DockerDesktop --silent --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -eq 0) {
        Ok "Docker Desktop installed"
        Warn "Restart Windows if Docker Desktop asks for it (WSL 2), then start it once."
    } else {
        Warn "Could not install Docker Desktop - get it from https://www.docker.com/products/docker-desktop/"
    }
} else {
    Warn "Docker Desktop is not installed - get it from https://www.docker.com/products/docker-desktop/"
}

# ---------------------------------------------------------------------------
Step "  [3/5]  Setting up the Python environment"
# ---------------------------------------------------------------------------
if (-not (Test-Path (Join-Path $Root 'src')) -or -not (Test-Path (Join-Path $Root 'docker_gui_modular.py'))) {
    Die "src\ or docker_gui_modular.py not found. The project may be incomplete - download it again."
}

function Test-Deps {
    if (-not (Test-Path $VenvPython)) { return $false }
    & $VenvPython -c "import tkinter, ttkbootstrap, PIL" *> $null
    return ($LASTEXITCODE -eq 0)
}

# A .venv copied from another machine points at a Python that is not there: rebuild it.
if ((Test-Path $Venv) -and -not (Test-Deps)) {
    Info "Existing .venv is unusable here - rebuilding it"
    Remove-Item -Recurse -Force $Venv
}
if (-not (Test-Path $Venv)) {
    & $py.Exe @($py.Prefix) -m venv $Venv
    if ($LASTEXITCODE -ne 0) { Die "Could not create the virtual environment at $Venv" }
}
& $VenvPython -m pip install --quiet --disable-pip-version-check -r (Join-Path $Root 'requirements.txt')
if ($LASTEXITCODE -ne 0) { Die "pip could not install the requirements (network down?). Run this again when online." }
if (-not (Test-Deps)) { Die "The Python dependencies installed but cannot be imported." }
Ok "Dependencies installed  ($Venv)"

# ---------------------------------------------------------------------------
Step "  [4/5]  Creating the Start Menu shortcut"
# ---------------------------------------------------------------------------
$programs = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$shortcut = Join-Path $programs 'Docker Control Panel.lnk'
try {
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($shortcut)
    $link.TargetPath = $VenvPythonW
    $link.Arguments = '"' + (Join-Path $Root 'docker_gui_modular.py') + '"'
    $link.WorkingDirectory = $Root
    $link.IconLocation = (Join-Path $Root 'assets\docker-icon.ico')
    $link.Description = 'GUI for Docker container management'
    $link.Save()
    Ok "Shortcut created  (Start menu -> Docker Control Panel)"
} catch {
    Warn "Could not create the Start Menu shortcut: $($_.Exception.Message)"
}

# ---------------------------------------------------------------------------
Step "  [5/5]  Creating the docker-gui command"
# ---------------------------------------------------------------------------
# WindowsApps is on every user's PATH by default, so no PATH editing is needed
$bin = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps'
try {
    Set-Content -Path (Join-Path $bin 'docker-gui.cmd') -Encoding ASCII -Value "@`"$(Join-Path $Root 'docker-gui.cmd')`" %*"
    Ok "Command created  (docker-gui)"
} catch {
    Warn "Could not create the docker-gui command: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Run the app:"
Write-Host "    1.  Start menu  ->  Docker Control Panel"
Write-Host "    2.  Terminal    ->  docker-gui"
Write-Host "    3.  Direct      ->  $Root\docker-gui.cmd"
Write-Host ""
