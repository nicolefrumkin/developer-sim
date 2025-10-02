import shutil
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

        # Run pytest as a subprocess (MVP; later run inside Docker)
        cmd = [sys.executable, "-m", "pytest", "-q"]
        try:
            proc = subprocess.run(
                cmd,
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=req.timeout_ms / 1000.0
            )
            stdout, stderr = proc.stdout, proc.stderr
            passed = (" 2 passed" in stdout) or (" 2 passed" in stderr)
            failed = (" failed" in stdout) or (" failed" in stderr)

            status = "passed" if proc.returncode == 0 else ("failed" if failed else "error")

            # Extremely simple parsing (MVP): if failed, attach stdout lines as feedback
            feedback = []
            if status != "passed":
                for i, line in enumerate(stdout.splitlines()[-10:], start=1):
                    feedback.append({"path": req.target_path, "line": i, "kind": "test-fail", "msg": line})

            finished_at = datetime.utcnow().isoformat() + "Z"
            return {
                "run_id": run_id,
                "ticket_id": req.ticket_id,
                "status": status,
                "feedback": feedback,
                "stats": { "tests_total": 2, "tests_passed": 2 if status=="passed" else 0, "time_ms": 0 },
                "artifacts": { "stdout": stdout, "stderr": stderr },
                "started_at": started_at,
                "finished_at": finished_at
            }
        except subprocess.TimeoutExpired:
            finished_at = datetime.utcnow().isoformat() + "Z"
            return {
                "run_id": run_id,
                "ticket_id": req.ticket_id,
                "status": "error",
                "feedback": [{"path": req.target_path, "line": 1, "kind": "runtime-error", "msg": "Timeout"}],
                "stats": {"tests_total": 2, "tests_passed": 0, "time_ms": req.timeout_ms},
                "artifacts": {"stdout": "", "stderr": "Timeout"},
                "started_at": started_at,
                "finished_at": finished_at
            }
