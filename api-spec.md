# API v1 (walking-skeleton)

Base URL: /v1
Content-Type: application/json

GET /v1/tickets/next
→ 200
{
  "id": "TCK-1",
  "title": "Implement sum(a,b)",
  "brief": "Return a+b for integers.",
  "files_seed": [
    { "path": "app/main.py", "content": "def sum(a,b):\n    pass\n" }
  ],
  "language": "python",
  "runtime": "python:3.12"
}

POST /v1/runs
Body:
{
  "ticket_id": "TCK-1",
  "code": "def sum(a,b):\n    return a+b\n",
  "target_path": "app/main.py",
  "timeout_ms": 15000
}
→ 200
{
  "run_id": "string",
  "ticket_id": "TCK-1",
  "status": "passed|failed|error",
  "feedback": [{ "path":"app/main.py","line":1,"kind":"test-fail|lint|runtime-error","msg":"..." }],
  "stats": {"tests_total": 1, "tests_passed": 1, "time_ms": 500},
  "started_at": "ISO-8601",
  "finished_at": "ISO-8601"
}

