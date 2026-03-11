# Lab 07 — Observability & Logging with Loki Stack Report

[![Ansible Deploy](https://github.com/AlliumPro/DevOps-Core-Course/actions/workflows/ansible-deploy.yml/badge.svg?branch=lab06)](https://github.com/AlliumPro/DevOps-Core-Course/actions/workflows/ansible-deploy.yml?query=branch%3Alab06)

> Deployed Loki 3.0 + Promtail 3.0 + Grafana 12.3, integrated JSON application logging, built production-ready Compose configuration, and implemented bonus Ansible role for monitoring stack automation.

---

## 1. Architecture

```text
Client traffic -> app-python (Flask, JSON logs)
                    |
                    v
             Docker container logs
                    |
                    v
             Promtail (docker_sd)
                    |
                    v
                Loki (TSDB)
                    |
                    v
             Grafana Explore + Dashboard
```

Runtime topology on VM:
- `app-python` on `:8000`
- `loki` on `:3100`
- `promtail` on `:9080`
- `grafana` on `:3000`

---

## 2. Setup Guide

### 2.1 Project Structure

```text
monitoring/
├── .env.example
├── docker-compose.yml
├── loki/config.yml
├── promtail/config.yml
├── grafana/provisioning/datasources/loki.yml
└── docs/LAB07.md
```

### 2.2 Deployment Steps

```bash
cd monitoring
cp .env.example .env
# Fill Grafana admin credentials in .env

# On target VM, compose binary was installed in user path:
mkdir -p ~/.local/bin
curl -fsSL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64 -o ~/.local/bin/docker-compose
chmod +x ~/.local/bin/docker-compose

~/.local/bin/docker-compose up -d --build
~/.local/bin/docker-compose ps
```

### 2.3 Health Verification

```bash
curl http://127.0.0.1:3100/ready
curl http://127.0.0.1:9080/targets
curl http://127.0.0.1:3000/api/health
```

Observed status (`docker-compose ps`):
- `loki` — `Up ... (healthy)`
- `grafana` — `Up ... (healthy)`
- `promtail` — `Up`
- `app-python` — `Up`

---

## 3. Configuration Details

### 3.1 Loki (`monitoring/loki/config.yml`)

Key choices:
- `store: tsdb` + `schema: v13` (Loki 3.0 recommended path)
- filesystem storage for single-node deployment
- retention set to `168h` (7 days)
- compactor enabled with delete request store (`boltdb`) for retention compatibility

Important snippet:
```yaml
schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13

limits_config:
  retention_period: 168h

compactor:
  retention_enabled: true
  delete_request_store: boltdb
```

### 3.2 Promtail (`monitoring/promtail/config.yml`)

- Docker service discovery via `/var/run/docker.sock`
- relabeling extracts `container` and `app`
- collection filtered to containers with label `logging=promtail`

Snippet:
```yaml
relabel_configs:
  - source_labels: [__meta_docker_container_label_logging]
    regex: promtail
    action: keep
```

### 3.3 Grafana Provisioning

Auto-provisioned Loki datasource in:
- `monitoring/grafana/provisioning/datasources/loki.yml`

---

## 4. Application Logging (JSON)

Updated Flask app in `app_python/app.py`:
- custom `JsonFormatter`
- request lifecycle logging:
  - `before_request` -> `request_started`
  - `after_request` -> `request_completed`
- fields included:
  - `timestamp`, `level`, `message`
  - `method`, `path`, `status_code`, `client_ip`, `duration_ms`, `request_id`

Example ingested log (from Loki query result):
```json
{"timestamp":"2026-03-11T18:28:39.515314+00:00","level":"INFO","logger":"devops-app","message":"request_completed","method":"GET","path":"/health","status_code":200,"client_ip":"94.177.9.115","duration_ms":3.84}
```

---

## 5. Dashboard & LogQL

Grafana data source:
- `Loki` (`http://loki:3100`)

Dashboard is provisioned from file:
- `monitoring/grafana/dashboards/lab07-logging.json`
- provider: `monitoring/grafana/provisioning/dashboards/dashboards.yml`

Panels included (as required):
1. Logs Table
2. Request Rate by App
3. Error Logs
4. Log Level Distribution

Queries used:
1. All app logs:
```logql
{app="devops-python"}
```

2. Parse JSON logs:
```logql
{app="devops-python"} | json
```

3. Request rate by app:
```logql
sum by (app) (rate({app=~"devops-.*"}[1m]))
```

4. Errors only:
```logql
{app=~"devops-.*"} | json | level="ERROR"
```

5. Level distribution:
```logql
sum by (level) (count_over_time({app=~"devops-.*"} | json [5m]))
```

---

## 6. Production Readiness

Implemented:
- resource limits/reservations for all services in `docker-compose.yml`
- Grafana anonymous auth disabled:
  - `GF_AUTH_ANONYMOUS_ENABLED=false`
- admin credentials from `.env`
- health checks:
  - Loki `/ready`
  - Grafana `/api/health`

---

## 7. Testing Evidence

### 7.1 Service and endpoint checks

```bash
~/.local/bin/docker-compose ps
curl -s http://127.0.0.1:3100/ready
curl -s http://127.0.0.1:3000/api/health
```

### 7.2 Log ingestion checks

```bash
# Generated traffic:
curl http://31.56.228.103:8000/
curl http://31.56.228.103:8000/health

# Loki label index:
curl http://127.0.0.1:3100/loki/api/v1/labels
# -> includes: app, container, service_name, stream

# app values:
curl http://127.0.0.1:3100/loki/api/v1/label/app/values
# -> ["devops-python"]
```

### 7.3 Loki query API sample

```bash
curl "http://127.0.0.1:3100/loki/api/v1/query_range?query=%7Bapp%3D%22devops-python%22%7D&limit=5"
```

Result contained JSON log entries from `app-python` container and request log lines.

### 7.4 Screenshots to attach before submission

1. Grafana Explore with query `{app="devops-python"}` and visible logs.
2. Grafana dashboard `Lab07 - Application Logging` with all 4 panels visible.
3. `docker-compose ps` output showing `loki` and `grafana` healthy.
4. Grafana login page proving anonymous access is disabled.

---

## 8. Challenges & Solutions

1. `docker compose` plugin missing on VM:
- Solution: installed user-space compose binary (`~/.local/bin/docker-compose`) without sudo.

2. Loki startup loop:
- Error: `compactor.delete-request-store should be configured when retention is enabled`
- Solution: added `delete_request_store: boltdb` in Loki compactor section.

3. Quoting issues in ad-hoc LogQL CLI tests:
- Solution: used URL-encoded query form for Loki API calls.

---

## 9. Bonus — Ansible Automation

Implemented bonus role:
- `ansible/roles/monitoring`
  - `defaults/main.yml`
  - `tasks/{main,setup,deploy}.yml`
  - `templates/{docker-compose,loki-config,promtail-config,grafana-datasource}.yml.j2`
  - `meta/main.yml`

Playbook:
- `ansible/playbooks/deploy-monitoring.yml`

Role behavior:
- creates monitoring directory structure
- templates Loki/Promtail/Grafana/Compose configs
- deploys stack with `community.docker.docker_compose_v2`
- waits for Loki and Grafana readiness via `uri`

---

## 10. Summary

Lab 07 main tasks are fully implemented in repository code and validated on target VM:
- Loki stack deployed and running
- application integrated with structured JSON logging
- logs ingested and queryable in Loki
- production hardening (security, resources, health checks)
- complete documentation prepared
- bonus Ansible monitoring automation implemented
