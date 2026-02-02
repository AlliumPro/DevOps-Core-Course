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

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the application

Default:

```bash
python app.py
```

Custom bind (example: host 127.0.0.1, port 8080):

```bash
PORT=8080 HOST=127.0.0.1 python app.py
# Or use gunicorn for production-like server
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## API Endpoints

- `GET /` - Service and system information (JSON)
- `GET /health` - Health check (JSON)

## Configuration

Environment variables:

| Variable | Default   | Description                                |
|----------|-----------|--------------------------------------------|
| `HOST`   | `0.0.0.0` | Address to bind the server                 |
| `PORT`   | `5000`    | TCP port for the web service               |
| `DEBUG`  | `false`   | Enable Flask debug mode when set to `true` |
