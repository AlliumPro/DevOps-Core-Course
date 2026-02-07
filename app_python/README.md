# DevOps Info Service

Lightweight Flask-based web service for the DevOps course. Provides system
and runtime information and a health endpoint for monitoring.

## Overview

This service returns detailed information about the host, runtime and
incoming requests. It's intended as the base service for further labs where
we'll containerize, add CI/CD, monitoring and persistence.

## Prerequisites

- Python 3.11+
- pip

## Installation

# DevOps Info Service

Lightweight Flask web service for the DevOps course. The app returns
service, system and runtime information and exposes a health endpoint used
by monitoring and Kubernetes probes.

## Overview

This repository contains a simple information service used in the course
labs. It is intentionally small so we can focus on containerization,
CI/CD and deployment practices in subsequent labs.

## Prerequisites

- Python 3.11+ (3.13 recommended)
- pip
- (optional) Docker to build and run the container

## Installation (local / development)

Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the application

Run locally (default binds to `0.0.0.0:5000`):

```bash
python3 app.py
```

Run on a custom host/port (example binds to `127.0.0.1:8080`):

```bash
PORT=8080 HOST=127.0.0.1 python3 app.py
```

Production note: use a WSGI server (gunicorn) for production-like testing:

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## API Endpoints

- `GET /` — service, system and runtime information (JSON)
- `GET /health` — simple health check (JSON)

Example quick checks:

```bash
curl -s http://127.0.0.1:5000/ | jq .
curl -s http://127.0.0.1:5000/health | jq .
```

## Configuration

Environment variables supported by the app:

| Variable | Default   | Description                                |
|----------|-----------|--------------------------------------------|
| `HOST`   | `0.0.0.0` | Address to bind the server                 |
| `PORT`   | `5000`    | TCP port for the web service               |
| `DEBUG`  | `false`   | Enable Flask debug mode when set to `true` |

## Docker (image & container)

Build the Docker image (from `app_python/`):

```bash
docker build -t alliumpro/devops-info-service:lab02 ./app_python
```

Run the container with port mapping:

```bash
docker run --rm -p 8080:5000 --name devops-info-service alliumpro/devops-info-service:lab02
```

Pull the published image from Docker Hub:

```bash
docker pull alliumpro/devops-info-service:lab02
```

## Troubleshooting

- If port 5000 is already in use on the host, run the container with a
	different host port (for example `-p 8080:5000`).
- If building fails due to Docker daemon issues, ensure Docker is running:

```bash
sudo systemctl start docker
sudo systemctl status docker
```

## Verification / Quick smoke test

1. Build and run the container as shown above.
2. Open the main endpoint in the browser or run:

```bash
curl -s http://127.0.0.1:8080/ | jq .
```

You should receive JSON similar to the example in the lab specification.