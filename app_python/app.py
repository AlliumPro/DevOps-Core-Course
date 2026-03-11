"""DevOps Info Service - Flask implementation for Lab 1 Task 1.

Provides two endpoints:
 - GET /      -> service, system and runtime information
 - GET /health -> simple health check used by probes

Configuration via environment variables: HOST, PORT, DEBUG
"""
from __future__ import annotations

import json
import logging
import os
import platform
import socket
import time
import uuid
from datetime import datetime, timezone
from typing import Dict

from flask import Flask, g, jsonify, request


APP_NAME = "devops-info-service"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "DevOps course info service"
FRAMEWORK = "Flask"


class JsonFormatter(logging.Formatter):
    """Serialize log records to JSON for structured aggregation in Loki."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
        }

        for attr in [
            "request_id",
            "method",
            "path",
            "status_code",
            "client_ip",
            "duration_ms",
        ]:
            value = getattr(record, attr, None)
            if value is not None:
                payload[attr] = value

        return json.dumps(payload, ensure_ascii=True)


def setup_logging() -> logging.Logger:
    logger_obj = logging.getLogger("devops-app")
    logger_obj.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))
    logger_obj.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger_obj.addHandler(handler)
    logger_obj.propagate = False
    return logger_obj


logger = setup_logging()

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


@app.before_request
def before_request_log() -> None:
    """Capture request start timing and emit ingress event."""
    g.request_start = time.perf_counter()
    g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    info = get_request_info()
    logger.info(
        "request_started",
        extra={
            "request_id": g.request_id,
            "method": info["method"],
            "path": info["path"],
            "client_ip": info["client_ip"],
        },
    )


@app.after_request
def after_request_log(response):
    """Emit request completion event with latency and status code."""
    started = getattr(g, "request_start", time.perf_counter())
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "request_completed",
        extra={
            "request_id": getattr(g, "request_id", None),
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "client_ip": request.headers.get("X-Forwarded-For", request.remote_addr or ""),
            "duration_ms": duration_ms,
        },
    )
    return response


@app.route("/")
def index():
    """Main endpoint returning service, system, runtime and request info."""
    logger.info("handle_index")

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
    logger.info("health_check")
    return jsonify(
        {
            "status": "healthy",
            "timestamp": timestamp,
            "uptime_seconds": uptime["seconds"],
        }
    ), 200


@app.errorhandler(404)
def not_found(e):
    logger.warning(
        "not_found",
        extra={
            "request_id": getattr(g, "request_id", None),
            "method": request.method,
            "path": request.path,
            "status_code": 404,
            "client_ip": request.headers.get("X-Forwarded-For", request.remote_addr or ""),
        },
    )
    return (
        jsonify({"error": "Not Found", "message": "Endpoint does not exist"}),
        404,
    )


@app.errorhandler(500)
def internal_error(e):
    logger.exception(
        "internal_error",
        extra={
            "request_id": getattr(g, "request_id", None),
            "method": request.method if request else None,
            "path": request.path if request else None,
            "status_code": 500,
        },
    )
    return (
        jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred"}),
        500,
    )


if __name__ == "__main__":
    logger.info(
        "app_start",
        extra={
            "app": APP_NAME,
            "version": APP_VERSION,
            "host": HOST,
            "port": PORT,
            "debug": DEBUG,
        },
    )
    # Flask 3.1 uses app.run as usual for development. In production, use a WSGI server.
    app.run(host=HOST, port=PORT, debug=DEBUG)
