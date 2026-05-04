$PORT = 8899
$ROOT = $PSScriptRoot

Write-Host "[restart] Killing any process on port $PORT..."
$pid = (netstat -aon | Select-String ":$PORT " | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -First 1)
if ($pid -and $pid -ne "0") {
    taskkill /F /PID $pid | Out-Null
    Write-Host "[restart] Killed PID $pid"
} else {
    Write-Host "[restart] No process found on port $PORT"
}

Write-Host "[restart] Starting Studio..."
Set-Location $ROOT
& "$ROOT\venv\Scripts\activate.ps1"
py -c "from src.podcast_server import launch_podcast_server; launch_podcast_server()"
