# DevOps Info Service ![Python CI](https://github.com/AlliumPro/DevOps-Core-Course/actions/workflows/python-ci.yml/badge.svg?branch=lab3)

Flask-based info service used throughout the DevOps core course. It reports service metadata, host information, runtime stats, exposes a `/health` endpoint for probes, and keeps a persisted visits counter.

## Features

- JSON payload describing the service, host OS/CPU, runtime uptime and request metadata
- Health endpoint for liveness/readiness checks
- Visits counter persisted in file storage (`/visits` endpoint)
- Dockerfile for reproducible builds
- Pytest suite covering `/`, `/health`, and error handling
- GitHub Actions workflow for lint → test → Docker build/push with CalVer tagging and optional Snyk scan

## Prerequisites

- Python 3.11+ (3.13 container image)
- pip
- (optional) Docker & Docker Hub account for publishing images

## Local setup

```bash
cd app_python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Running the app

```bash
# default: 0.0.0.0:5000
python3 app.py

# custom host/port
HOST=127.0.0.1 PORT=8080 python3 app.py

# production-style
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Testing & linting

```bash
# run tests
pytest -q

# run tests with coverage (optional)
pytest --cov=app_python --cov-report=term-missing

# lint
flake8 app_python
```

## API quick check

```bash
curl -s http://127.0.0.1:5000/ | jq .
curl -s http://127.0.0.1:5000/health | jq .
curl -s http://127.0.0.1:5000/visits | jq .
```

## Configuration

| Variable | Default   | Purpose                              |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Address to bind the Flask server |
| `PORT` | `5000`    | TCP port                           |
| `DEBUG` | `false`  | Enables Flask debug mode          |
| `VISITS_FILE` | `/data/visits` | Path to persisted visits counter file |

## Docker usage

```bash
# build (from repo root)
docker build -t alliumpro/devops-info-service:lab02 ./app_python

# run
docker run --rm -p 8080:5000 alliumpro/devops-info-service:lab02

# pull published image
docker pull alliumpro/devops-info-service:lab02
```

## Docker Compose persistence test

`docker-compose.yml` in this directory mounts host folder `./data` into container `/data`.

```bash
# from repository root
docker compose -f app_python/docker-compose.yml up -d --build

# generate traffic
curl -s http://127.0.0.1:8080/
curl -s http://127.0.0.1:8080/
curl -s http://127.0.0.1:8080/visits

# verify persisted file on host
cat app_python/data/visits

# restart service and verify value remains
docker compose -f app_python/docker-compose.yml restart
curl -s http://127.0.0.1:8080/visits
```

## CI/CD workflow

Workflow file: `.github/workflows/python-ci.yml`

Pipeline stages:
1. Checkout + Python setup (3.11)
2. Pip cache restore → install dependencies (prod + dev)
3. Lint via `flake8`
4. Pytest suite (fail-fast)
5. Snyk dependency scan (runs when `SNYK_TOKEN` secret is configured)
6. Build & push Docker image with CalVer + `latest` tags (main/master branch)

### Required GitHub secrets

| Secret | Description |
| --- | --- |
| `DOCKERHUB_USERNAME` | Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token with write perms |
| `DOCKERHUB_REPO` | Target repo, e.g. `alliumpro/devops-info-service` |
| `SNYK_TOKEN` | API token to enable the Snyk scan step |

## Troubleshooting

- **Port already in use** → set `PORT` or use `docker run -p 8080:5000`.
- **Docker daemon unavailable** → `sudo systemctl start docker`.
- **CI push skipped** → workflow only pushes on `main`/`master` (or tags); ensure secrets are configured.