<#  One-shot dev bootstrap for Job Sim (Windows / PowerShell)
    Run from repo root:
      .\scripts\dev.ps1
#>
Write-Host ">>> dev.ps1 STARTED" -ForegroundColor Yellow

$ErrorActionPreference = "Stop"

function Write-Header($msg) {
  Write-Host "`n== $msg ==" -ForegroundColor Cyan
}

# --- Config ---
$RedisName = "jobsim-redis"
$RunnerImage = "jobsim-runner:py312"
$RunnerDockerfile = "backend/runner/Dockerfile.runner"   # path per project README
$VenvPath = ".\.venv"
$ApiPort = 8000
$FrontendPort = 3000
$StartFrontend = $true   # set to $false if you don’t want the frontend window

# --- Helpers ---
function Ensure-Program($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "$name not found. Please install it and re-run."
  }
}

function Ensure-DockerRunning {
  Write-Header "Checking Docker"
  Ensure-Program docker
  try { docker ps > $null } catch { throw "Docker Desktop is not running." }
}

function Ensure-RunnerImage {
  Write-Header "Building sandbox image ($RunnerImage)"
  $exists = docker images --format "{{.Repository}}:{{.Tag}}" | Select-String -SimpleMatch $RunnerImage
  if (-not $exists) {
    docker build -t $RunnerImage -f $RunnerDockerfile .
  } else {
    Write-Host "Image already present. Rebuilding for freshness..."
    docker build -t $RunnerImage -f $RunnerDockerfile .
  }
}

function Ensure-Redis {
  Write-Header "Starting Redis ($RedisName)"
  $running = docker ps --format "{{.Names}}" | Where-Object { $_ -eq $RedisName }
  $exists  = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $RedisName }

  if ($running) {
    Write-Host "Redis already running."
  } elseif ($exists) {
    Write-Host "Redis container exists but is stopped. Starting..."
    docker start $RedisName | Out-Null
  } else {
    docker run -d --name $RedisName -p 6379:6379 redis:7 | Out-Null
  }
}

function Ensure-VenvAndDeps {
  Write-Header "Preparing Python venv + deps"
  Ensure-Program python
  if (-not (Test-Path $VenvPath)) {
    python -m venv $VenvPath
  }
  & "$VenvPath\Scripts\python.exe" -m pip install --upgrade pip
  & "$VenvPath\Scripts\pip.exe" install fastapi "uvicorn[standard]" redis rq pydantic
}

function Start-WorkerWindow {
  Write-Header "Starting Worker"
  $venvPy = Join-Path $PWD ".venv\Scripts\python.exe"
  $cmd = @"
& `"$venvPy`" -m backend.worker.worker
"@
  Start-Process -WindowStyle Normal -FilePath "powershell.exe" -ArgumentList "-NoExit","-Command",$cmd
}

function Start-ApiWindow {
  Write-Header "Starting API (port $ApiPort)"
  $venvPy = Join-Path $PWD ".venv\Scripts\python.exe"
  $cmd = @"
& `"$venvPy`" -m uvicorn backend.app.main:app --reload --port $ApiPort
"@
  Start-Process -WindowStyle Normal -FilePath "powershell.exe" -ArgumentList "-NoExit","-Command",$cmd
}


function Start-FrontendWindow {
  if (-not $StartFrontend) { return }
  if (-not (Test-Path ".\frontend\package.json")) {
    Write-Host "frontend/ not found. Skipping frontend." -ForegroundColor Yellow
    return
  }
  Write-Header "Starting Frontend (port $FrontendPort)"

  # Build the command that will run in the new PowerShell window.
  # NOTE: This is a double-quoted here-string; variables like $ApiPort are expanded now.
  $cmd = @"
cd `"$PWD\frontend`"
if (!(Test-Path node_modules)) { npm install }

# Ensure API base is present (overwrite to keep things in sync)
`$envLine = 'NEXT_PUBLIC_API_BASE=http://127.0.0.1:$ApiPort'
Set-Content -Path .env.local -Value `$envLine -Encoding UTF8

npm run dev
"@

  Start-Process -WindowStyle Normal -FilePath "powershell.exe" -ArgumentList "-NoExit","-Command",$cmd
}

# --- Run all steps ---
Ensure-DockerRunning
Ensure-RunnerImage
Ensure-Redis
Ensure-VenvAndDeps
Start-WorkerWindow
Start-ApiWindow
Start-FrontendWindow

# Open browser to frontend
Start-Process "http://localhost:3000"

Write-Header "All set!"
Write-Host "Worker + API launched in new windows. Frontend on http://localhost:$FrontendPort (if enabled)."
Write-Host "API docs at http://localhost:$ApiPort/docs"
