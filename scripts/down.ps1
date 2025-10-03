# Close spawned PowerShell windows (API/Worker) by title match (best-effort)
Get-Process powershell | Where-Object { $_.MainWindowTitle -match "uvicorn|backend\.worker\.worker|npm run dev" } | Stop-Process -Force -ErrorAction SilentlyContinue

# Stop and remove Redis container
docker stop jobsim-redis 2>$null | Out-Null
docker rm jobsim-redis 2>$null | Out-Null

Write-Host "Stopped worker/API windows (best-effort) and removed Redis container."
