"""DevOps Info Service - Flask implementation for Lab 1 Task 1.

Provides two endpoints:
 - GET /      -> service, system and runtime information
 - GET /health -> simple health check used by probes

Configuration via environment variables: HOST, PORT, DEBUG
"""
from __future__ import annotations

import logging
import os
import platform
import socket
from datetime import datetime, timezone
from typing import Dict

from flask import Flask, jsonify, request


APP_NAME = "devops-info-service"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "DevOps course info service"
FRAMEWORK = "Flask"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration from environment
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Application start time (UTC)
START_TIME = datetime.now(timezone.utc)


def get_uptime() -> Dict[str, object]:
    """Return uptime in seconds and human readable form."""
    delta = datetime.now(timezone.utc) - START_TIME
    seconds = int(delta.total_seconds())
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    human = f"{hours} hours, {minutes} minutes"
    return {"seconds": seconds, "human": human}


def get_system_info() -> Dict[str, object]:
    """Collect system and runtime information."""
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "unknown"

    system = platform.system()
    platform_version = platform.version()
    arch = platform.machine()
    cpu_count = os.cpu_count() or 1
    python_version = platform.python_version()

    return {
        "hostname": hostname,
        "platform": system,
        "platform_version": platform_version,
        "architecture": arch,
        "cpu_count": cpu_count,
        "python_version": python_version,
    }


def get_request_info() -> Dict[str, object]:
    """Extract useful request information (works in Flask)."""
    # Prefer X-Forwarded-For if behind a proxy
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        client_ip = xff.split(",")[0].strip()
    else:
        client_ip = request.remote_addr or ""

    return {
        "client_ip": client_ip,
        "user_agent": request.headers.get("User-Agent", ""),
        "method": request.method,
        "path": request.path,
    }


@app.route("/")
def index():
    """Main endpoint returning service, system, runtime and request info."""
    logger.info("Handling main endpoint request: %s %s", request.method, request.path)

    uptime = get_uptime()
    now = datetime.now(timezone.utc).isoformat()

    payload = {
        "service": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "description": APP_DESCRIPTION,
            "framework": FRAMEWORK,
        },
        "system": get_system_info(),
        "runtime": {
            "uptime_seconds": uptime["seconds"],
            "uptime_human": uptime["human"],
            "current_time": now,
            "timezone": "UTC",
        },
        "request": get_request_info(),
        "endpoints": [
            {"path": "/", "method": "GET", "description": "Service information"},
            {"path": "/health", "method": "GET", "description": "Health check"},
        ],
    }

    return jsonify(payload)


@app.route("/health")
def health():
    """Simple health endpoint suitable for liveness/readiness probes."""
    uptime = get_uptime()
    timestamp = datetime.now(timezone.utc).isoformat()
    logger.debug("Health check requested")
    return jsonify(
        {
            "status": "healthy",
            "timestamp": timestamp,
            "uptime_seconds": uptime["seconds"],
        }
    ), 200


@app.errorhandler(404)
def not_found(e):
    logger.warning("404 Not Found: %s", request.path)
    return (
        jsonify({"error": "Not Found", "message": "Endpoint does not exist"}),
        404,
    )


@app.errorhandler(500)
def internal_error(e):
    logger.exception("Unhandled exception occurred")
    return (
        jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred"}),
        500,
    )


if __name__ == "__main__":
    logger.info("Starting %s on %s:%s (debug=%s)", APP_NAME, HOST, PORT, DEBUG)
    # Flask 3.1 uses app.run as usual for development. In production, use a WSGI server.
    app.run(host=HOST, port=PORT, debug=DEBUG)
