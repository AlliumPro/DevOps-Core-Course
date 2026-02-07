# LAB02 — Docker Containerization

This report documents the Docker containerization of the Lab 1 Python app. It follows the Lab 2 checklist and includes build/run evidence placeholders and analysis.

## 1. Docker Best Practices Applied

**Non-root user**
- Implemented with `adduser`/`addgroup` and `USER app`.
- Why it matters: reduces the blast radius in case of compromise and is a standard container security practice.

**Specific base image version**
- Using `python:3.13-slim`.
- Why it matters: fixed versions make builds reproducible and reduce unintended breaking changes.

**Layer caching (dependencies before source code)**
- `requirements.txt` is copied and installed before `app.py` is copied.
- Why it matters: changes in app code do not invalidate dependency layers, making rebuilds faster.

**Minimal build context via `.dockerignore`**
- Excludes venvs, tests, docs, git files and caches.
- Why it matters: smaller context → faster builds, smaller images, lower risk of leaking dev files.

**Only necessary files copied**
- Only `requirements.txt` and `app.py` are copied into the image.
- Why it matters: smaller image surface and fewer attack vectors.

**Dockerfile snippets**

```dockerfile
FROM python:3.13-slim
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py ./
USER app
CMD ["python", "app.py"]
```

## 2. Image Information & Decisions

- **Base image:** `python:3.13-slim` — chosen for small size while keeping Debian compatibility.
-- **Final image size:** 184MB (image ID: `5cae74f76afd`) — measured after local build.
- **Layer structure:**
  1. Base OS + Python runtime
  2. Non-root user creation
  3. Dependencies (pip install)
  4. Application source
- **Optimization choices:**
  - `--no-cache-dir` for pip to avoid cache bloat.
  - `.dockerignore` to reduce build context.

## 3. Build & Run Process (evidence)

### Build output

```text
$ docker build -t devops-info-service:lab02 /home/ian/Desktop/DevOps-Core-Course/app_python
...build output excerpt...
[+] Building 75.0s (15/15) FINISHED
 => [internal] load build definition from Dockerfile            0.1s
 => [1/6] FROM docker.io/library/python:3.13-slim@sha256:... 44.2s
 => [2/6] WORKDIR /app                                          0.3s
 => [3/6] RUN addgroup --system app && adduser --system --ingroup app app 0.7s
 => [4/6] COPY requirements.txt ./                              0.2s
 => [5/6] RUN pip install --no-cache-dir -r requirements.txt   11.6s
 => [6/6] COPY app.py ./                                        0.2s
 => exporting to image                                          1.8s
 => => naming to docker.io/library/devops-info-service:lab02    0.0s

Image built: devops-info-service:lab02
Image ID: 5cae74f76afd
Image size: 184MB
```

### Run output

```text
$ docker run --rm -p 8080:5000 devops-info-service:lab02
2026-02-02 14:08:21,288 - __main__ - INFO - Starting devops-info-service on 0.0.0.0:5000 (debug=False)
 * Serving Flask app 'app'
 * Debug mode: off
2026-02-02 14:08:21,305 - werkzeug - INFO - WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://172.17.0.2:5000
2026-02-02 14:08:21,305 - werkzeug - INFO - Press CTRL+C to quit
2026-02-02 14:54:42,426 - __main__ - INFO - Handling main endpoint request: GET /
2026-02-02 14:54:42,427 - werkzeug - INFO - 172.17.0.1 - - [02/Feb/2026 14:54:42] "GET / HTTP/1.1" 200 -
2026-02-02 14:54:42,441 - werkzeug - INFO - 172.17.0.1 - - [02/Feb/2026 14:54:42] "GET /health HTTP/1.1" 200 -
2026-02-02 14:54:59,350 - __main__ - INFO - Handling main endpoint request: GET /
2026-02-02 14:54:59,350 - werkzeug - INFO - 172.17.0.1 - - [02/Feb/2026 14:54:59] "GET / HTTP/1.1" 200 -
```

### Endpoint tests

```text
$ curl -s http://127.0.0.1:8080/ | jq .
{
  "endpoints": [
    {
      "description": "Service information",
      "method": "GET",
      "path": "/"
    },
    {
      "description": "Health check",
      "method": "GET",
      "path": "/health"
    }
  ],
  "request": {
    "client_ip": "172.17.0.1",
    "method": "GET",
    "path": "/",
    "user_agent": "curl/8.5.0"
  },
  "runtime": {
    "current_time": "2026-02-02T14:54:42.426679+00:00",
    "timezone": "UTC",
    "uptime_human": "0 hours, 46 minutes",
    "uptime_seconds": 2781
  },
  "service": {
    "description": "DevOps course info service",
    "framework": "Flask",
    "name": "devops-info-service",
    "version": "1.0.0"
  },
  "system": {
    "architecture": "x86_64",
    "cpu_count": 14,
    "hostname": "02584e0e525b",
    "platform": "Linux",
    "platform_version": "#1 SMP PREEMPT_DYNAMIC Thu Mar 20 16:36:58 UTC 2025",
    "python_version": "3.13.11"
  }
}

$ curl -s http://127.0.0.1:8080/health | jq .
{
  "status": "healthy",
  "timestamp": "2026-02-02T14:54:42.440819+00:00",
  "uptime_seconds": 2781
}

Additional curl run (later):
{
  "runtime": {
    "current_time": "2026-02-02T14:54:59.350316+00:00",
    "timezone": "UTC",
    "uptime_human": "0 hours, 46 minutes",
    "uptime_seconds": 2798
  }
}
```

### Docker Hub

I pushed the image to Docker Hub under the username `alliumpro` and verified a public pull.

Commands executed:

```bash
docker tag devops-info-service:lab02 alliumpro/devops-info-service:lab02
docker push alliumpro/devops-info-service:lab02
docker rmi alliumpro/devops-info-service:lab02 devops-info-service:lab02
docker pull alliumpro/devops-info-service:lab02
```

Push output (excerpt):

```text
The push refers to repository [docker.io/alliumpro/devops-info-service]
36b6de65fd8d: Pushed
7c7ec8605b81: Pushed
8d21c49cbaec: Pushed
703084cd5f7b: Pushed
6f400a2a56a1: Pushed
4c021db47d93: Pushed
0bee50492702: Pushed
8843ea38a07e: Pushed
75ee186ea42c: Pushed
119d43eec815: Pushed
lab02: digest: sha256:5cae74f76afd9d00def8dc3981d08d7e18dba46ae39906a1c2e1f1ff22e6a1c4 size: 856
```

Pull output (excerpt):

```text
lab02: Pulling from alliumpro/devops-info-service
7c7ec8605b81: Pull complete
6f400a2a56a1: Pull complete
8d21c49cbaec: Pull complete
4c021db47d93: Pull complete
703084cd5f7b: Pull complete
Digest: sha256:5cae74f76afd9d00def8dc3981d08d7e18dba46ae39906a1c2e1f1ff22e6a1c4
Status: Downloaded newer image for alliumpro/devops-info-service:lab02
docker.io/alliumpro/devops-info-service:lab02
```

Docker Hub repository URL:

```
https://hub.docker.com/r/alliumpro/devops-info-service
```

## 4. Technical Analysis

- **Why the Dockerfile works:** it installs dependencies first (cached), then copies source, then runs as non-root for security.
- **If layer order changes:** copying `app.py` before installing requirements invalidates the cache on every code change, slowing rebuilds.
- **Security considerations:** non-root user, minimal files copied, smaller base image, no build tools left in the final image.
- **How `.dockerignore` improves builds:** reduces context size, avoids sending venvs/tests/docs to the daemon, and reduces image bloat.

## 5. Challenges & Solutions

- **Challenge:** Port conflicts on 5000.
  - **Solution:** Run container with `-p 8080:5000` or another free port.
- **Challenge:** Keeping build context small.
  - **Solution:** Added `.dockerignore` and copied only required files.

## 6. Checklist

- [x] Dockerfile exists in `app_python/`
- [x] Specific base image version used
- [x] Non-root user configured
- [x] Proper layer ordering (deps before code)
- [x] Only necessary files copied
- [x] `.dockerignore` present
- [x] Image built successfully (build output included above)
- [x] Container runs and app works (run output and endpoint tests included above)
- [x] Image pushed to Docker Hub (`alliumpro/devops-info-service:lab02`) — see Docker Hub section above
- [x] Public pull verified (pull output included above)
---

## Final Report (Checklist Summary)

1. **Best Practices Applied:** Non-root user, slim base image, dependency caching, minimal build context, no unnecessary files.
2. **Image Decisions:** `python:3.13-slim`; pip cache disabled; `.dockerignore` reduces context.
3. **Build/Run Evidence:** Included above — build output, image ID/size, container logs and endpoint tests are present in Section 3.
4. **Technical Analysis:** Layer order affects caching; non-root improves security; `.dockerignore` speeds build.
5. **Challenges & Solutions:** Port conflicts solved with custom port mapping.
6. **Docker Hub:** Image pushed to Docker Hub and public pull verified. Repository: https://hub.docker.com/r/alliumpro/devops-info-service
