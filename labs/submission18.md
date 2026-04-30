# Lab 18 - Reproducible Builds with Nix

> Completed on 30 Apr 2026 on Windows 11 + WSL2 (`Ubuntu 24.04.3 LTS`).  
> Main goal: rebuild the Lab 1/2 Python service with Nix, prove reproducibility, compare it with `pip`/`venv` and a classic `Dockerfile`, then modernize the setup with Flakes.

---

## 1. Environment and final result

| Item | Value |
| --- | --- |
| Host OS | Windows 11 |
| Linux environment | WSL2 / Ubuntu 24.04.3 LTS |
| Nix version | `nix (Nix) 2.18.1` |
| Docker version | `Docker 28.0.4` |
| Application source reused from | `app_python/` (Labs 1-2) |
| Lab 18 app copy | `labs/lab18/app_python/` |
| Main deliverable | `labs/submission18.md` |
| Bonus deliverables | `labs/lab18/app_python/flake.nix`, `labs/lab18/app_python/flake.lock` |

Files created for this lab:

- `labs/lab18/app_python/default.nix`
- `labs/lab18/app_python/docker.nix`
- `labs/lab18/app_python/flake.nix`
- `labs/lab18/app_python/flake.lock`

Screenshots:

- `labs/lab18/screenshots/01-nix-local-app.png`
- `labs/lab18/screenshots/02-dockerfile-app.png`
- `labs/lab18/screenshots/03-nix-docker-app.png`

Important implementation note:
- outside containers the app originally wanted to write visits to `/data/visits`
- that is inconvenient for a Nix-built local binary because the build output is immutable and `/data` may not exist
- therefore the wrapper in `default.nix` sets `VISITS_FILE=/tmp/devops-info-service-visits` by default
- for the Docker image built with Nix, `docker.nix` sets `VISITS_FILE=/work/visits`

---

## 2. Task 1 - Reproducible Python build

### 2.1 Installing and checking Nix

The lab suggests the Determinate Systems installer. I tried that path first, but in this WSL environment the installer download repeatedly timed out.  
To keep the lab executable and still get a real Nix installation, I installed the distro packages and enabled flakes manually:

```bash
apt-get update
apt-get install -y nix-bin nix-setup-systemd
mkdir -p ~/.config/nix
echo "experimental-features = nix-command flakes" > ~/.config/nix/nix.conf
```

Verification:

```bash
nix --version
nix run nixpkgs#hello
```

Observed output:

```text
nix (Nix) 2.18.1
Hello, world!
```

### 2.2 Preparing the Lab 1 application

I copied the existing service into the lab directory:

```bash
mkdir -p labs/lab18/app_python
cp -r app_python/* labs/lab18/app_python/
```

Reused files:

- `app.py`
- `requirements.txt`
- `Dockerfile`
- `tests/test_app.py`

### 2.3 Nix derivation

The core build expression is `labs/lab18/app_python/default.nix`.

What it does:

- imports `pkgs` from `nixpkgs`
- pins the runtime to `python312`
- creates a Python runtime environment with:
  - `flask`
  - `gunicorn`
  - `python-json-logger`
  - `prometheus-client`
- filters mutable noise from the source tree:
  - `data/visits`
  - `__pycache__/`
  - `.pytest_cache/`
  - `result*`
- runs the existing test suite during `checkPhase`
- installs a wrapped executable `devops-info-service`

Why I used a wrapper:

- the app is a plain `app.py`, not a package with `setup.py`/`pyproject.toml`
- wrapping the interpreter is the cleanest way to run it as a reproducible binary
- it also lets me inject safe runtime defaults like `PORT=5000`

### 2.4 Building and running the application

Build command:

```bash
cd labs/lab18/app_python
nix-build
```

Result:

```text
/nix/store/7nhq4pggr2i4gs6zp59s4g0cw2s6ki73-devops-info-service-1.0.0
```

Tests were executed during the build:

```text
.......                                                                  [100%]
7 passed in 0.67s
```

Running the Nix-built app:

```bash
./result/bin/devops-info-service
curl http://127.0.0.1:5000/health
```

Health response:

```json
{"status":"healthy","timestamp":"2026-04-30T16:21:28.622872+00:00","uptime_seconds":2}
```

Screenshot:

- `labs/lab18/screenshots/01-nix-local-app.png`

### 2.5 Proof of reproducibility

I repeated the build three times and forced a real rebuild by deleting the store path:

```bash
FIRST=/nix/store/7nhq4pggr2i4gs6zp59s4g0cw2s6ki73-devops-info-service-1.0.0
SECOND=/nix/store/7nhq4pggr2i4gs6zp59s4g0cw2s6ki73-devops-info-service-1.0.0
THIRD=/nix/store/7nhq4pggr2i4gs6zp59s4g0cw2s6ki73-devops-info-service-1.0.0
```

Store deletion output:

```text
1 store paths deleted, 0.01 MiB freed
```

Hash of the final output:

```text
262805e7fa1fa4c549d7eac457247ed6fe102e7e4d41d38433c4298b175cc7f5
```

Conclusion:

- first build produced a store path
- second build reused the exact same store path
- after deleting the built output and rebuilding, the exact same store path came back
- therefore the derivation is deterministic for the same inputs

### 2.6 Comparing with the Lab 1 `pip` workflow

Traditional Lab 1 workflow:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

#### Experiment A - unpinned requirement

I intentionally created `requirements-unpinned.txt` with only:

```text
flask
```

Two fresh virtual environments produced:

```text
Flask==3.1.3
Jinja2==3.1.6
MarkupSafe==3.0.3
Werkzeug==3.1.8
blinker==1.9.0
click==8.3.3
itsdangerous==2.2.0
```

Both installs matched **today**, but that does **not** make the workflow reproducible:

- the file only says `flask`
- the resolved version came from the current PyPI state
- the transitive dependency set also came from the current PyPI state
- the same command next week or next month may resolve to a different tree

#### Experiment B - original `requirements.txt`

Original direct requirements:

```text
Flask==3.1.0
gunicorn==21.2.0
python-json-logger==2.0.7
prometheus-client==0.23.1
```

But a real installed environment contained more than that:

```text
Flask==3.1.0
Jinja2==3.1.6
MarkupSafe==3.0.3
Werkzeug==3.1.8
blinker==1.9.0
click==8.3.3
gunicorn==21.2.0
itsdangerous==2.2.0
packaging==26.2
prometheus_client==0.23.1
python-json-logger==2.0.7
```

This is the exact weakness the lab describes:

- `requirements.txt` pins only direct dependencies
- transitive packages still arrive via resolver behavior
- the environment is not content-addressed
- the venv itself is machine-local and not portable

### 2.7 Why Nix is stronger here

| Aspect | `pip` + `venv` | Nix derivation |
| --- | --- | --- |
| Python version | Depends on machine | Pinned by derivation |
| Direct dependencies | Partially pinned | Pinned in Nix expression |
| Transitive dependencies | Resolver outcome | Part of exact closure |
| Build environment | Mutable | Isolated |
| Rebuild identity | Not guaranteed | Same inputs -> same store path |
| Binary cache | No real equivalent | Native Nix feature |

### 2.8 Understanding the Nix store path

Example:

```text
/nix/store/7nhq4pggr2i4gs6zp59s4g0cw2s6ki73-devops-info-service-1.0.0
```

Parts:

- `/nix/store` - immutable global store
- `7nhq4pggr2i4gs6zp59s4g0cw2s6ki73` - content-derived hash
- `devops-info-service` - package name
- `1.0.0` - version label

Meaning:

- if source, dependencies, or build instructions change, the hash changes
- if nothing changes, the path remains the same

### 2.9 Reflection for Task 1

If I had used Nix from the start in Lab 1:

- the app environment would have been reproducible immediately
- I would not depend on host Python state
- onboarding on another machine would be simpler
- the difference between "my machine" and "CI machine" would shrink drastically

---

## 3. Task 2 - Reproducible Docker images

### 3.1 Baseline from Lab 2

Traditional container source:

- `app_python/Dockerfile`

It uses:

- `FROM python:3.13-slim`
- `pip install -r requirements.txt`
- app copy into `/app`
- non-root user `app`

That is a good normal Dockerfile, but it is not a cryptographically reproducible build description.

### 3.2 Nix Docker image

The Nix image expression is `labs/lab18/app_python/docker.nix`.

Important fields:

- `buildLayeredImage`
- `name = "devops-info-service-nix"`
- `tag = "1.0.0"`
- `contents = [ app pkgs.bash pkgs.coreutils ]`
- `config.Cmd = [ "${app}/bin/devops-info-service" ]`
- `config.ExposedPorts."5000/tcp" = {}`
- `created = "1970-01-01T00:00:01Z"`

Why `created` matters:

- timestamps are a classic source of non-determinism
- fixing the creation timestamp keeps the tarball stable across rebuilds

### 3.3 Reproducible Nix image build

Built twice with Flakes:

```bash
nix build path:/.../labs/lab18/app_python#dockerImage --out-link result-docker-1
nix build path:/.../labs/lab18/app_python#dockerImage --out-link result-docker-2
```

Both outputs resolved to the same tarball:

```text
PATH=/nix/store/ss0vpnxd9n7j61nz97hh2nmkgiqdbjx8-devops-info-service-nix.tar.gz
SHA256=4422793c838cce99c909f5ddcf62e465b676f41d6e69bca5d291e457ce6f74f5
```

Second build:

```text
PATH=/nix/store/ss0vpnxd9n7j61nz97hh2nmkgiqdbjx8-devops-info-service-nix.tar.gz
SHA256=4422793c838cce99c909f5ddcf62e465b676f41d6e69bca5d291e457ce6f74f5
```

This is the cleanest proof in the whole lab: same flake + same inputs -> same image tarball bit-for-bit.

### 3.4 Comparing with the traditional Docker build

#### Cached rebuilds

Two normal cached Docker builds produced different saved-image hashes:

```text
v1 docker save sha256: 859e283e4d430978fa9d4e8dd10d90c6eb30d4ceb863f894cb21da87a50a77a2
v2 docker save sha256: 692a4d0e9ceac54d87a38da59085200b0bb656f05c7e762e4dabc2de9901afa9
```

Interesting nuance:

- BuildKit cache made the visible `Created=` timestamp stay the same for these two cached rebuilds
- but the serialized image output still changed
- so even without source changes, the classic Docker workflow did not give me a bit-identical archive

#### Forced no-cache rebuilds

To make the non-determinism even more obvious, I also built twice with `--no-cache`:

```text
Created=2026-04-30T16:45:38.1631582Z Size=45118754
Created=2026-04-30T16:46:09.460396829Z Size=45118737
```

Saved-image hashes:

```text
nc1: 79132bd54d51caec163fa542b69e65b961fda9dfba56e66419bb36b821e56211
nc2: 8d19cc5b534ed8dfb76535a22208f3bcd0a9f0b684b82637480d36a2b5f9dce4
```

This is exactly the behavior the lab warns about:

- timestamps differ
- image metadata differs
- serialized archives differ

### 3.5 Loading and running both images

Load Nix image:

```bash
docker load < result-docker-2
```

Loaded image metadata:

```text
Created=1970-01-01T00:00:01Z Size=196769136
```

Run side by side:

```bash
docker run -d -p 5000:5000 --name lab2-container lab2-app:v1
docker run -d -p 5001:5000 --name nix-container devops-info-service-nix:1.0.0
```

Health checks:

```text
LAB2_HEALTH
{"status":"healthy","timestamp":"2026-04-30T17:11:28.904903+00:00","uptime_seconds":4}

NIX_HEALTH
{"status":"healthy","timestamp":"2026-04-30T17:11:28.934763+00:00","uptime_seconds":4}
```

Screenshots:

- `labs/lab18/screenshots/02-dockerfile-app.png`
- `labs/lab18/screenshots/03-nix-docker-app.png`

### 3.6 Image size comparison

`docker images` on this machine showed:

```text
lab2-app:v1                 186MB
devops-info-service-nix     406MB
```

Observed result:

- in **this** implementation the Nix image is larger, not smaller
- the reason is that the image contains the pinned Nix Python closure instead of relying on a distro base that Docker already treats as a reusable layer
- the tradeoff here is reproducibility first, size second

This is still a valid and useful result:

- Nix solved determinism
- it did not automatically optimize image size
- minimizing the closure further would be the next iteration

### 3.7 History analysis

Traditional Docker history:

- shows relative creation times like `6 minutes ago`, `8 days ago`, `9 days ago`
- includes base-image lineage such as `python:3.13-slim`
- inherits mutable distro state over time

Nix image history:

- shows `N/A` in the created column
- layers are described by exact store paths
- comments explicitly mention the Nix store closure

This is the most important conceptual difference:

- Docker history describes how an image was assembled
- Nix history describes the immutable closure that defines the image content

### 3.8 Task 2 comparison table

| Aspect | Traditional Dockerfile | Nix `dockerTools` |
| --- | --- | --- |
| Base image | `python:3.13-slim` | No mutable distro base tag |
| Timestamp behavior | Can drift | Fixed `created` timestamp |
| Dependency install | `pip install` during image build | Pre-built Nix closure |
| Reproducibility proof | Failed (`docker save` hashes differed) | Passed (same tar hash twice) |
| Image history | Relative times + mutable base lineage | Store paths + deterministic layering |
| Size on my machine | `186MB` | `406MB` |

### 3.9 Reflection for Task 2

If I redid Lab 2 with Nix:

- I would still keep the normal Dockerfile for teaching the classic workflow
- but for CI/CD releases I would prefer the Nix-built image
- the biggest benefit is not convenience, it is confidence:
  - rollback is clearer
  - audit is easier
  - "same source, same image" stops being a hope and becomes a property

---

## 4. Bonus - Flakes and comparison with Lab 10

### 4.1 Flake files

Files:

- `labs/lab18/app_python/flake.nix`
- `labs/lab18/app_python/flake.lock`

Locked `nixpkgs` state from `flake.lock`:

```json
{
  "owner": "NixOS",
  "repo": "nixpkgs",
  "rev": "50ab793786d9de88ee30ec4e4c24fb4236fc2674",
  "narHash": "sha256-/bVBlRpECLVzjV19t5KMdMFWSwKLtb5RyXdjz3LJT+g="
}
```

That means the package set is not just "24.11 in general" - it is a concrete revision and content hash.

### 4.2 Building through the flake

Commands:

```bash
nix build path:/.../labs/lab18/app_python#default
nix build path:/.../labs/lab18/app_python#dockerImage
```

Resolved package output:

```text
/nix/store/7nhq4pggr2i4gs6zp59s4g0cw2s6ki73-devops-info-service-1.0.0
```

### 4.3 Development shell

Command:

```bash
nix develop path:/.../labs/lab18/app_python
```

Inside the dev shell I verified:

```text
Python 3.12.8
Flask 3.0.3
prometheus-client 0.21.0
```

This is a good example of the Nix model:

- the shell is reproducible
- package versions come from locked `nixpkgs`
- the environment is portable as code

### 4.4 Comparison with Lab 10 Helm values

In Lab 10 we pinned deployment values like:

```yaml
image:
  repository: your-image
  tag: "1.0.0"
```

That helps, but it only locks the container reference.

What `flake.lock` locks:

- exact `nixpkgs` revision
- Python runtime version
- dependency graph
- build tooling
- full closure hash

### 4.5 Bonus comparison table

| Aspect | Lab 1 `venv` | Lab 10 Helm values | Lab 18 Flakes |
| --- | --- | --- | --- |
| Locks Python version | No | No | Yes |
| Locks direct app deps | Partially | No | Yes |
| Locks transitive deps | No | No | Yes |
| Locks build tooling | No | No | Yes |
| Cross-machine reproducibility | Weak | Medium | Strong |
| Dev environment support | Yes | No | Yes |

### 4.6 Bonus reflection

Flakes are the most complete answer in this lab because they combine:

- reproducible package definitions
- a lock file
- a build interface
- a dev shell

This is much closer to "infrastructure and build environment as code" than the earlier labs.

---

## 5. Problems encountered and how I solved them

1. **Determinate installer timeout in WSL**
   - the recommended installer could not complete because downloads were too slow in this environment
   - I switched to Ubuntu packages `nix-bin` + `nix-setup-systemd`

2. **`python3.13` package compatibility in the chosen package set**
   - the initial `python313` variant pulled a broken combination during the Nix build
   - I moved to `python312`, which built cleanly and kept the lab reproducible

3. **Nested flake inside a dirty Git repository**
   - building the flake via plain `nix build .#...` from a nested untracked directory was unreliable
   - I used path-based flake URIs:
     - `path:/mnt/c/.../labs/lab18/app_python#default`
     - `path:/mnt/c/.../labs/lab18/app_python#dockerImage`

4. **Docker reproducibility is more subtle with BuildKit cache**
   - two cached builds kept the same visible `Created=` timestamp
   - but `docker save` still produced different hashes
   - to make the point undeniable, I also ran `--no-cache` builds

---

## 6. Final checklist

- [x] Nix installed and verified
- [x] Lab 1 Python service copied into `labs/lab18/app_python/`
- [x] `default.nix` created
- [x] App built with `nix-build`
- [x] Existing tests executed during Nix build
- [x] Reproducibility proven with repeated builds and forced rebuild
- [x] `pip` / `venv` limitations analyzed
- [x] `docker.nix` created
- [x] Nix Docker image built twice with identical tarball hash
- [x] Traditional Docker image compared against Nix image
- [x] Both images run successfully and answer `/health`
- [x] Bonus completed with `flake.nix` and `flake.lock`
- [x] Comparison with Lab 10 Helm pinning included

---

## 7. Short conclusion

This lab clearly showed the difference between **repeatable commands** and **reproducible artifacts**.

- `pip install -r requirements.txt` is workable, but not cryptographically stable
- a normal `Dockerfile` is convenient, but still vulnerable to time, registry, and metadata drift
- Nix gives a much stronger guarantee: same inputs -> same store path -> same image tarball

For me, the most convincing proof was this pair:

```text
/nix/store/7nhq4pggr2i4gs6zp59s4g0cw2s6ki73-devops-info-service-1.0.0
SHA256(262805e7fa1fa4c549d7eac457247ed6fe102e7e4d41d38433c4298b175cc7f5)
```

and

```text
/nix/store/ss0vpnxd9n7j61nz97hh2nmkgiqdbjx8-devops-info-service-nix.tar.gz
SHA256(4422793c838cce99c909f5ddcf62e465b676f41d6e69bca5d291e457ce6f74f5)
```

That is the core outcome of Lab 18.
