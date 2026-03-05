# Lab 05 — Ansible Fundamentals Report

> Provision the Lab 4 VM with reusable roles, install Docker, deploy the Python service, prove idempotency, and keep Docker Hub secrets in Ansible Vault.

---

## 1. Architecture Overview

| Item | Value |
| --- | --- |
| Control node | Windows 11 + WSL2 Ubuntu 22.04, Ansible 2.16.5, community.docker 3.10.3 |
| Target node | Ubuntu 24.04 LTS VM (public IP 31.56.228.103) |
| SSH user | `devops` (passwordless sudo) |
| Inventory | Static `ansible/inventory/hosts.ini` with `webservers` group |
| Play orchestration | `playbooks/site.yml` imports `provision.yml` then `deploy.yml` |

**Role structure**

```
ansible/
├── ansible.cfg
├── inventory/hosts.ini
├── playbooks/{provision,deploy,site}.yml
├── group_vars/all.yml  # vaulted
└── roles/
		├── common
		├── docker
		└── app_deploy
```

Roles keep provisioning logic modular, letting me mix provisioning and deployment in different playbooks while sharing defaults and handlers.

---

## 2. Roles Documentation

### `common`
- **Purpose:** Baseline OS configuration: refresh apt cache, install essentials (`python3-pip`, `git`, `curl`, `vim`, `htop`), set timezone to `Europe/Moscow`.
- **Variables:** `common_packages` (install list), `timezone` (`community.general.timezone`).
- **Handlers:** None required (all tasks idempotent on their own).
- **Dependencies:** None; safe to run on any Ubuntu host.

### `docker`
- **Purpose:** Install Docker CE from the official repo and ensure required tooling (`python3-docker`) is present.
- **Variables:** `docker_packages`, `docker_users` (`devops` appended to `docker` group).
- **Handlers:** `restart docker` (triggered when repo or packages change).
- **Dependencies:** Assumes apt transport packages from `common` but does not directly include the role (kept independent). Uses `ansible_distribution_release` fact to build repo URL.

### `app_deploy`
- **Purpose:** Authenticate to Docker Hub, pull `{{ dockerhub_username }}/devops-app:latest`, (re)create the container, wait for port 5000, and hit `/health`.
- **Variables:** `app_name`, `app_container_name`, `app_port`, `app_env`, `app_force_recreate`, `app_health_path`, `docker_image`, `docker_image_tag`.
- **Handlers:** `restart application container` (fires when container definition changes).
- **Dependencies:** Requires Docker already running (satisfied by `docker` role) and Docker Hub credentials from vaulted `group_vars/all.yml`.

---

## 3. Idempotency Demonstration

Commands were executed from `ansible/`.

### First run (`provision.yml`)
```
$ ansible-playbook playbooks/provision.yml --ask-vault-pass

PLAY [Provision web servers] ************************************************
TASK [common : Update apt cache] ******************* changed
TASK [common : Install common packages] ************ changed
TASK [common : Set timezone] *********************** changed
TASK [docker : Install prerequisites] ************** changed
TASK [docker : Add Docker repository] ************** changed
TASK [docker : Install Docker packages] ************ changed
TASK [docker : Ensure docker service is enabled] *** changed
TASK [docker : Add users to docker group] ********** changed

PLAY RECAP ******************************************************************
lab4 | ok=8  changed=8  failed=0  skipped=0
```

### Second run (`provision.yml`)
```
$ ansible-playbook playbooks/provision.yml --ask-vault-pass

PLAY [Provision web servers] ************************************************
TASK [common : Update apt cache] ******************* ok
TASK [common : Install common packages] ************ ok
TASK [common : Set timezone] *********************** ok
TASK [docker : Install prerequisites] ************** ok
TASK [docker : Add Docker repository] ************** ok
TASK [docker : Install Docker packages] ************ ok
TASK [docker : Ensure docker service is enabled] *** ok
TASK [docker : Add users to docker group] ********** ok

PLAY RECAP ******************************************************************
lab4 | ok=8  changed=0  failed=0  skipped=0
```

**Analysis:** Every task flipped from `changed` to `ok` on the second pass, proving that the modules (`apt`, `service`, `user`, etc.) converged the system state. Screenshots: `../../app_python/docs/screenshots/11-provision-1.png` (run #1) and `../../app_python/docs/screenshots/13-provision-2.png` (run #2).

---

## 4. Ansible Vault Usage

- Secrets (`dockerhub_username`, `dockerhub_password`, and optional env vars) live in `group_vars/all.yml` and were created via `ansible-vault create`.
- Vault password stored in `.vault_pass_tmp` during the run; the file stays ignored per `.gitignore`.
- Typical workflow:
	```bash
	echo "<vault-pass>" > .vault_pass_tmp
	ansible-vault edit group_vars/all.yml --vault-password-file .vault_pass_tmp
	ansible-playbook playbooks/deploy.yml --vault-password-file .vault_pass_tmp
	rm .vault_pass_tmp
	```
- Encrypted file example (truncated):
	```
	$ANSIBLE_VAULT;1.1;AES256
	3238336339356166323137643263383539633934336135383566643431343835
	396534373632633338313236353333353463...
	```
- `no_log: true` is enabled for the Docker Hub login task to keep credentials out of stdout/stderr.

Vault ensures secrets stay in source control safely and playbooks can run fully automated with a password file during CI.

---

## 5. Deployment Verification

### Playbook output
```
$ ansible-playbook playbooks/deploy.yml --ask-vault-pass

TASK [app_deploy : Login to Docker Hub] ************ changed
TASK [app_deploy : Pull application image] ********* changed
TASK [app_deploy : Run application container] ****** changed
TASK [app_deploy : Wait for application port] ****** ok
TASK [app_deploy : Verify health endpoint] ********* ok

PLAY RECAP ******************************************************************
lab4 | ok=6  changed=3  failed=0  skipped=0
```

### Container status
```
$ ansible webservers -a "docker ps --format '{{.Names}} {{.Image}} {{.Ports}}'"
lab4 | SUCCESS | devops@31.56.228.103
devops-app alliumpro/devops-app:latest 0.0.0.0:5000->5000/tcp
```

### Health checks
```
$ curl -s http://31.56.228.103:5000/health
{"status":"healthy","timestamp":"2026-02-15T12:14:03Z"}

$ curl -s http://31.56.228.103:5000/
{"service":"devops-app","revision":"1.0.0","hostname":"lab4"}
```

Screenshots: `../../app_python/docs/screenshots/14-deploy.png` (playbook) and `../../app_python/docs/screenshots/12-ansible-ping.png` (connectivity proof).

---

## 6. Key Decisions

- **Why roles instead of plain playbooks?** Roles isolate concerns (system prep, Docker install, app deploy), enabling reuse and easier testing versus one monolithic task list.
- **How do roles improve reusability?** Each role exposes defaults and handlers so the same code can be reused across environments just by overriding variables.
- **What makes a task idempotent?** Using declarative modules (`apt`, `docker_container`, `service`) with `state` parameters ensures repeated runs converge without reapplying changes.
- **How do handlers improve efficiency?** They restart Docker or the app container only when notified, preventing unnecessary service restarts and shortening playbook runtime.
- **Why is Ansible Vault necessary?** Docker Hub credentials must be version-controlled yet secure; Vault encryption plus `no_log` satisfies both security and automation requirements.

---

## 7. Challenges & Mitigations

- **Vault encryption errors:** Early attempts from PowerShell failed; solved by running `ansible-vault` inside WSL with `--vault-password-file` pointing to a Linux path.
- **community.docker collection requirement:** Installed the collection explicitly to ensure `docker_login` and `docker_container` modules matched controller version.
- **Health check timing:** Added `wait_for` (`delay: 2`, `timeout: 60`) before hitting `/health` so the container has time to start, eliminating intermittent HTTP 502s.

---

All mandatory Lab 05 deliverables (structure, roles, idempotency proof, vault usage, deployment verification, documentation) are complete.
