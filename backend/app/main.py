import time
import shutil
from rq import Queue
import redis
from backend.worker.worker import run_in_container
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from starlette.responses import JSONResponse as StarletteJSONResponse
from pydantic import BaseModel
from datetime import datetime
import subprocess, tempfile, os, json, uuid, textwrap, sys, shlex

class PrettyJSONResponse(StarletteJSONResponse):
    def render(self, content) -> bytes:
        # indent=2 makes it multi-line and readable
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=2
        ).encode("utf-8")

app = FastAPI(
    title="Workday Sim API v1",
    version="0.1",
    default_response_class=PrettyJSONResponse
)

# --------- Models ---------
class SeedFile(BaseModel):
    path: str
    content: str

class RunRequest(BaseModel):
    ticket_id: str
    code: str
    target_path: str
    timeout_ms: int = 15000

# --------- Hard-coded Ticket #1 ---------
TICKET_1 = {
    "id": "TCK-1",
    "title": "Implement sum(a,b)",
    "brief": "Return a+b for integers.",
    "files_seed": [ {"path": "app/main.py", "content": "def sum(a,b):\n    pass\n"} ],
    "language": "python",
    "runtime": "python:3.12"
}

TEST_FILE = textwrap.dedent("""
    from app.main import sum

    def test_sum_basic():
        assert sum(1,2) == 3

    def test_negatives():
        assert sum(-2,5) == 3
""")

rconn = redis.from_url("redis://localhost:6379/0")
runs_q = Queue("runs", connection=rconn)

# --------- Endpoints ---------
@app.get("/v1/tickets/next")
def get_next_ticket():
    return TICKET_1

@app.post("/v1/runs")
def run_tests(req: RunRequest):
    if req.ticket_id != "TCK-1":
        raise HTTPException(status_code=400, detail="Unknown ticket_id")

    run_id = f"run_{uuid.uuid4().hex}"
    started_at = datetime.utcnow().isoformat() + "Z"

    # Create temp workspace
    with tempfile.TemporaryDirectory() as tmp:
        # Make package structure
        os.makedirs(os.path.join(tmp, "app"), exist_ok=True)

        # Write user code to target path
        target_abs = os.path.join(tmp, *req.target_path.split("/"))
        with open(target_abs, "w", encoding="utf-8") as f:
            f.write(req.code)

        # Write test file
        tests_dir = os.path.join(tmp, "tests")
        os.makedirs(tests_dir, exist_ok=True)
        with open(os.path.join(tests_dir, "test_main.py"), "w", encoding="utf-8") as f:
            f.write(TEST_FILE)

        # Minimal pyproject to make pytest happy
        with open(os.path.join(tmp, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write('[tool.pytest.ini_options]\naddopts = "-q"\n')

        # ---- Run tests inside Docker sandbox ----
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",           # no internet
            "--cpus", "1",                 # limit CPU
            "--memory", "512m",            # limit RAM
            "--pids-limit", "128",         # process limit
            "-v", f"{tmp}:/workspace:ro",  # mount temp workspace read-only
            "devsim-runner:py312"          # your image
        ]

        # ---- Enqueue job to the worker ----
        payload = {
            "ticket_id": req.ticket_id,
            "code": req.code,
            "target_path": req.target_path,
            "timeout_ms": req.timeout_ms,
            "tests": TEST_FILE
        }

        # enqueue by dotted path so the API doesn’t import Docker stuff
        job = runs_q.enqueue(run_in_container, payload)

        deadline = time.time() + (req.timeout_ms/1000.0) + 2  # a tiny grace period
        result = None

        while time.time() < deadline:
            # refresh cached data from Redis
            job.refresh()
            status = job.get_status()  # 'queued' | 'started' | 'deferred' | 'finished' | 'failed' | ...
            if status in ("finished", "failed"):
                result = job.result  # dict returned by run_in_container (or None if failed before returning)
                break
            time.sleep(0.2)  # poll interval

        if result is None:
            # timeout or no result
            return {
                "run_id": job.id,
                "ticket_id": req.ticket_id,
                "status": "error",
                "feedback": [{
                    "path": req.target_path,
                    "line": 1,
                    "kind": "runtime-error",
                    "msg": f"Runner timeout or no result (job status: {job.get_status()})"
                }],
                "stats": {"tests_total": 0, "tests_passed": 0, "time_ms": req.timeout_ms},
                "artifacts": {"stdout": "", "stderr": ""}
            }

        # success path: add timestamps if you want
        result["started_at"] = started_at
        result["finished_at"] = datetime.utcnow().isoformat() + "Z"
        return result


