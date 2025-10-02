# Developer Sim — walking skeleton

A tiny “work-day simulator” slice: an API gives **Ticket #1** and runs your code in a safe **Docker** sandbox, returning **pass/fail + feedback**.

## Quick start (Windows / PowerShell)

**Prereqs:** Docker Desktop, Python 3.12+, Git.
This project uses **Redis** (we’ll run it in Docker).

```powershell
# 1) Clone & enter
git clone https://github.com/nicolefrumkin/developer-sim.git
cd developer-sim

# 2) Build the sandbox image (pytest, ruff, etc.)
docker build -t devsim-runner:py312 -f backend/runner/Dockerfile.runner .

# 3) Start Redis
docker run -d --name devsim-redis -p 6379:6379 redis:7

# 4) Python deps (API + worker)
python -m venv .venv
.\.venv\Scripts\activate
pip install fastapi "uvicorn[standard]" redis rq pydantic
```

Open **two terminals**:

**Terminal A – Worker (stay in repo root):**

```powershell
.\.venv\Scripts\activate
python -m backend.worker.worker
```

**Terminal B – API:**

```powershell
.\.venv\Scripts\activate
uvicorn backend.app.main:app --reload --port 8000
```

## Try it

**Terminal C - Get next ticket**

```powershell
Invoke-RestMethod http://localhost:8000/v1/tickets/next
```

**Run code for Ticket #1**

```powershell
$body = @{
  ticket_id = "TCK-1"
  code = "def sum(a,b): return a+b"
  target_path = "app/main.py"
  timeout_ms = 15000
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/v1/runs -Method POST -Body $body -ContentType "application/json"
```

You should get JSON with `status: "passed"` (or `failed` with feedback).

## Notes

* If you see a **timeout**: confirm the worker is running and the image `devsim-runner:py312` exists.
* API docs: see `infra/api-spec.md`.
