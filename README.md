# Job Sim — Quick Start

## Run the app

Open **PowerShell** in the project root and run:

```powershell
.\scripts\dev.ps1
```

This will:

* Build the Docker runner image

* Start Redis in Docker

* Create a Python virtual environment + install dependencies

* Launch the Worker, API, and Frontend in separate windows

* **API:** [http://localhost:8000](http://localhost:8000) (docs at `/docs`)

* **Frontend:** [http://localhost:3000](http://localhost:3000)

---

## Stop the app

When you’re done, run:

```powershell
.\scripts\down.ps1
```

This will close the worker/API/frontend windows (best effort) and stop/remove the Redis container.
