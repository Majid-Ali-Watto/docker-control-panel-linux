# Docker Control Panel - Windows uninstaller (the project folder itself is kept)
$Root = $PSScriptRoot
$items = @(
    (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Docker Control Panel.lnk'),
    (Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\docker-gui.cmd'),
    (Join-Path $Root '.venv')
)
foreach ($item in $items) {
    if (Test-Path $item) { Remove-Item -Recurse -Force $item; Write-Host "  removed  $item" -ForegroundColor Green }
    else { Write-Host "  not found  $item" -ForegroundColor Yellow }
}
Write-Host ""
Write-Host "Uninstallation complete. Your project folder was NOT deleted:"
Write-Host "  $Root"
Write-Host "Saved settings live in $env:USERPROFILE\.docker-gui (delete it to remove them)."
