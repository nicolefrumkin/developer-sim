import os, tempfile, subprocess, sys, uuid

from rq import Queue, Worker
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def run_in_container(payload: dict) -> dict:
    ticket_id = payload["ticket_id"]
    code = payload["code"]
    target_path = payload["target_path"]
    timeout_ms = payload.get("timeout_ms", 15000)
    tests_str = payload["tests"]

    run_id = f"run_{uuid.uuid4().hex}"

    import os, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        # write user code
        os.makedirs(os.path.join(tmp, "app"), exist_ok=True)
        with open(os.path.join(tmp, *target_path.split("/")), "w", encoding="utf-8") as f:
            f.write(code)

        # write tests
        os.makedirs(os.path.join(tmp, "tests"), exist_ok=True)
        with open(os.path.join(tmp, "tests", "test_main.py"), "w", encoding="utf-8") as f:
            f.write(tests_str)

        # run pytest inside the sandbox image
        docker_cmd = [
            "docker","run","--rm",
            "--network","none","--cpus","1","--memory","512m","--pids-limit","128",
            "-v", f"{tmp}:/workspace:ro",
            "devsim-runner:py312"
        ]

        try:
            proc = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=timeout_ms/1000.0)
            stdout, stderr = proc.stdout, proc.stderr
            status = "passed" if proc.returncode == 0 else "failed"
            feedback = []
            if status != "passed":
                for i, line in enumerate(stdout.splitlines()[-20:], start=1):
                    feedback.append({"path": target_path, "line": i, "kind": "test-fail", "msg": line})
            return {
                "run_id": run_id,
                "ticket_id": ticket_id,
                "status": status,
                "feedback": feedback,
                "stats": {"tests_total": 2, "tests_passed": 2 if status == "passed" else 0, "time_ms": 0},
                "artifacts": {"stdout": stdout, "stderr": stderr},
            }
        except subprocess.TimeoutExpired:
            return {
                "run_id": run_id,
                "ticket_id": ticket_id,
                "status": "error",
                "feedback": [{"path": target_path, "line": 1, "kind": "runtime-error", "msg": "Timeout"}],
                "stats": {"tests_total": 2, "tests_passed": 0, "time_ms": timeout_ms},
                "artifacts": {"stdout": "", "stderr": "Timeout"},
            }

if __name__ == "__main__":
    r = redis.from_url(REDIS_URL)
    q = Queue("runs", connection=r)
    worker = Worker([q], connection=r)
    worker.work()
