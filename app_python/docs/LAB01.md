# LAB01 - DevOps Info Service (Task 1)

This document describes the implementation of Task 1 (Python web application)
for the DevOps course. The service is implemented using Flask and provides a
main `/` endpoint with detailed service/system/runtime information and a
`/health` endpoint for monitoring.

## Framework selection

- Chosen framework: **Flask 3.1**

Reasons for Flask:
- Lightweight and well-known in educational contexts.
- Simple to extend with logging, health checks and configuration.
- Minimal surface area - ideal for iteratively adding DevOps tooling.

Comparison with alternatives:

| Framework | Advantages | Trade-offs | Verdict for Lab 1 |
|-----------|------------|------------|-------------------|
| Flask     | Minimal setup, synchronous by default, rich ecosystem | Needs manual docs generation |  Chosen - balances simplicity and control |
| FastAPI   | Async support, auto-generated docs (OpenAPI), type hints | Slight learning curve for async; more dependencies |  Overkill for two simple endpoints |
| Django    | Batteries included (ORM, admin, auth) | Heavyweight, requires project scaffolding |  Too much ceremony for a lightweight info service |

## What I implemented (requirements coverage)

- `GET /` - returns JSON with `service`, `system`, `runtime`, `request`, and
	`endpoints` sections. (Done)
- `GET /health` - returns `status`, `timestamp`, and `uptime_seconds`.
	(Done)
- Environment-configurable `HOST`, `PORT`, `DEBUG`. (Done)
- Logging and basic error handlers for 404 and 500. (Done)

Files changed/added:
- `app.py` - main Flask application and endpoints
- `requirements.txt` - pinned dependencies (`Flask==3.1.0`, `gunicorn`)
- `README.md` - usage and run instructions
- `.gitignore` - common Python ignores

## Task 2 — Documentation & Best Practices

1. Application README (`app_python/README.md`) — Required sections:
	- Overview — present
	- Prerequisites — present (Python 3.11+)
	- Installation — present (venv + pip install)
	- Running the Application — present with examples (including custom PORT/HOST)
	- API Endpoints — present
	- Configuration — present (table with `HOST`, `PORT`, `DEBUG`)

	Status: Done. See `app_python/README.md` for the full user-facing instructions.

2. Best Practices implemented in code:
	- Clean code organization with helper functions (`get_system_info`, `get_uptime`, `get_request_info`) — Done (`app.py`).
	- Error handling with JSON responses for 404 and 500 — Done (`app.py`).
	- Logging configuration and usage (INFO level) — Done (`app.py`).
	- Dependencies pinned in `requirements.txt` — Done.

3. Lab Submission (`app_python/docs/LAB01.md`) — This report includes:
	- Framework selection and comparison — present above.
	- Best practices applied with code snippets — present above.
	- API documentation with examples — present above.
	- Testing evidence instructions and screenshot checklist — present below.
	- Challenges & Solutions — present above.

## Best practices applied

1. **Configuration via environment variables (12-factor app principle).**

	```python
	HOST = os.getenv("HOST", "0.0.0.0")
	PORT = int(os.getenv("PORT", 5000))
	DEBUG = os.getenv("DEBUG", "False").lower() == "true"
	```

2. **Clear function separation (`get_system_info`, `get_uptime`, `get_request_info`).**

	```python
	def get_system_info() -> Dict[str, object]:
		 return {
			  "hostname": socket.gethostname(),
			  "platform": platform.system(),
			  "architecture": platform.machine(),
			  "python_version": platform.python_version(),
		 }
	```

3. **Timezone-aware timestamps and uptime calculations.**

	```python
	START_TIME = datetime.now(timezone.utc)
	delta = datetime.now(timezone.utc) - START_TIME
	```

4. **Structured logging.**

	```python
	logging.basicConfig(
		 level=logging.INFO,
		 format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
	)
	logger.info("Handling main endpoint request: %s %s", request.method, request.path)
	```

5. **JSON error handlers for better API UX.**

	```python
	@app.errorhandler(404)
	def not_found(e):
		 return jsonify({"error": "Not Found", "message": "Endpoint does not exist"}), 404
	```

## API Documentation and examples

1) GET /

Request:

```bash
curl -s http://127.0.0.1:5000/
```

Response (example):

```json
{
	"service": {"name": "devops-info-service", "version": "1.0.0", "description": "DevOps course info service", "framework": "Flask"},
	"system": {"hostname": "my-host", "platform": "Linux", "platform_version": "#1 SMP ...", "architecture": "x86_64", "cpu_count": 4, "python_version": "3.11.4"},
	"runtime": {"uptime_seconds": 12, "uptime_human": "0 hours, 0 minutes", "current_time": "2026-01-25T12:00:00+00:00", "timezone": "UTC"},
	"request": {"client_ip": "127.0.0.1", "user_agent": "curl/7.81.0", "method": "GET", "path": "/"},
	"endpoints": [{"path": "/", "method": "GET", "description": "Service information"}, {"path": "/health", "method": "GET", "description": "Health check"}]
}
```

2) GET /health

Request:

```bash
curl -s http://127.0.0.1:5000/health
```

Response (example):

```json
{
	"status": "healthy",
	"timestamp": "2026-01-25T12:00:05+00:00",
	"uptime_seconds": 15
}
```

## How to run locally

1. Create and activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`.
3. Run the app: `python app.py` (default binds to `0.0.0.0:5000`).

Or using gunicorn (4 workers):

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Testing evidence

Place screenshots taken while manually testing the endpoints in
`app_python/docs/screenshots/` as required by the lab. Capture:

1. `01-main-endpoint.png` - browser showing the full JSON from `GET /`.
2. `02-health-check.png` - response from `GET /health` (status + uptime).
3. `03-formatted-output.png` - pretty-printed output

Quick local checks (after `python3 app.py`):

```bash
curl -s http://127.0.0.1:8080/ | jq .
curl -s http://127.0.0.1:8080/health | jq .
python3 -m py_compile app.py
```

Outcome: commands completed without errors (syntax check passes, endpoints return JSON that matches the schema above).

## Challenges & Solutions

- Challenge: Ensuring timestamps and uptime are timezone-aware and stable.
	Solution: Use `datetime.now(timezone.utc)` and store a UTC `START_TIME`.
- Challenge: Getting the correct client IP behind proxies.
	Solution: Prefer `X-Forwarded-For` header when present, with a safe
	fallback to Flask's `request.remote_addr`.

## GitHub Community

- Starring the course repository and `simple-container-com/api` surfaces them
	in your network, signaling support and making it easier to discover future
	updates or issues to contribute to.
- Following the professor, TAs and classmates keeps their activity in your
	feed, which helps coordination on team projects and exposes you to career
	opportunities or best practices they share.