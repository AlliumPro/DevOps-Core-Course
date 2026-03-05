# Lab 06 — Advanced Ansible & CI/CD Report

[![Ansible Deploy](https://github.com/AlliumPro/DevOps-Core-Course/actions/workflows/ansible-deploy.yml/badge.svg?branch=lab06)](https://github.com/AlliumPro/DevOps-Core-Course/actions/workflows/ansible-deploy.yml?query=branch%3Alab06)

> Refactored Lab 5 automation with blocks/tags, migrated app deployment to Docker Compose, implemented safe wipe logic, and added GitHub Actions deployment pipeline.

---

## 1. Overview

| Item | Value |
| --- | --- |
| Base from previous labs | Lab 04 VM + Lab 05 Ansible roles |
| Control environment | Windows 11 (PowerShell workspace editing) |
| Target node | Ubuntu 24.04 VM (`31.56.228.103`) |
| Main upgrade | `app_deploy` role renamed to `web_app` + Compose v2 deployment |
| CI/CD | `.github/workflows/ansible-deploy.yml` |

**Implemented structure**

```text
ansible/
├── docs/LAB06.md
├── group_vars/all.yml
├── playbooks/
│   ├── provision.yml
│   ├── deploy.yml
│   └── deploy_python.yml
├── vars/
│   └── app_python.yml
└── roles/
    ├── common/
    ├── docker/
    └── web_app/
        ├── defaults/main.yml
        ├── meta/main.yml
        ├── tasks/main.yml
        ├── tasks/wipe.yml
        ├── templates/docker-compose.yml.j2
        └── handlers/main.yml
```

---

## 2. Blocks & Tags (Task 1)

### `common` role refactor
File: `roles/common/tasks/main.yml`

- Package installation grouped in block with tag `packages`.
- Added `rescue` for apt failures:
  - `apt-get update --fix-missing`
  - retry apt cache update.
- Added `always` section writing completion marker to `/tmp/ansible-common-packages.log`.
- Added user management block with tag `users`.
- Role-level tag `common` applied from `playbooks/provision.yml`.

Added defaults in `roles/common/defaults/main.yml`:
- `common_users` (default: `devops`)
- existing `common_packages`, `timezone` preserved.

### `docker` role refactor
File: `roles/docker/tasks/main.yml`

- Installation tasks grouped in block with tag `docker_install`.
- Runtime config grouped in block with tag `docker_config`.
- Added `rescue` path for transient GPG/repo failures:
  - wait 10 seconds
  - refresh apt cache
  - retry GPG key + repo + package install.
- Added `always` section to force Docker service state convergence (`enabled` + `started`).
- Role-level tag `docker` applied from `playbooks/provision.yml`.

Updated `roles/docker/defaults/main.yml`:
- Added `docker-compose-plugin` to `docker_packages`.

### Tag usage examples

```bash
cd ansible
ansible-playbook playbooks/provision.yml --list-tags
ansible-playbook playbooks/provision.yml --tags "docker"
ansible-playbook playbooks/provision.yml --tags "docker_install"
ansible-playbook playbooks/provision.yml --tags "packages"
ansible-playbook playbooks/provision.yml --skip-tags "common"
```

---

## 3. Docker Compose Migration (Task 2)

### Rename and role migration
- Renamed role directory: `roles/app_deploy` → `roles/web_app`.
- Updated deployment playbook role reference:
  - `playbooks/deploy.yml` now uses `web_app`.

### Compose template
File: `roles/web_app/templates/docker-compose.yml.j2`

- Jinja2 template with dynamic fields:
  - `app_name`
  - `docker_image:docker_image_tag`
  - `app_port:app_internal_port`
  - `app_env`
  - `restart` policy
- Adds `PORT={{ app_internal_port }}` to guarantee app bind port consistency.

### Role dependency
File: `roles/web_app/meta/main.yml`

```yaml
dependencies:
  - role: docker
```

This guarantees Docker is available before `web_app` tasks run.

### Compose deployment implementation
File: `roles/web_app/tasks/main.yml`

Deployment block now performs:
1. Docker Hub login (`no_log: true`)
2. Create app directory (`compose_project_dir`)
3. Template Compose file
4. `community.docker.docker_compose_v2` with `state: present`, `pull: always`
5. `wait_for` on service port
6. Health check via `uri`

Tags used:
- `app_deploy`
- `compose`
- `web_app` (playbook role tag)

### Variables
- `roles/web_app/defaults/main.yml` defines app/compose/wipe defaults.
- `group_vars/all.yml` defines shared vars and credentials loading.
- App-specific deployment variables stored in `vars/app_python.yml`.

---

## 4. Wipe Logic (Task 3)

### Implementation
Files:
- `roles/web_app/tasks/wipe.yml`
- `roles/web_app/tasks/main.yml` (include at top)
- `roles/web_app/defaults/main.yml` (`web_app_wipe: false`)

Wipe flow (`wipe.yml`):
1. `docker_compose_v2 state=absent`
2. remove `docker-compose.yml`
3. remove project directory
4. log completion (`debug`)

Safety model:
- Variable gate: `when: web_app_wipe | bool`
- Tag gate: `web_app_wipe`
- No `never` tag used (per requirement).

### Test scenarios (commands)

**Scenario 1 — normal deploy (wipe skipped by default variable):**
```bash
ansible-playbook playbooks/deploy.yml
```

**Scenario 2 — wipe only:**
```bash
ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true" --tags web_app_wipe
```

**Scenario 3 — clean reinstall (wipe → deploy):**
```bash
ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true"
```

**Scenario 4a — tag only with default variable false (safe skip):**
```bash
ansible-playbook playbooks/deploy.yml --tags web_app_wipe
```

---

## 5. CI/CD Integration (Task 4)

### Workflow 1: Python app deployment
File: `.github/workflows/ansible-deploy.yml`

Pipeline stages:
1. **Lint job**
   - install `ansible-core`, `ansible-lint`
   - install collections `community.docker`, `community.general`
   - run `ansible-lint` over playbooks/roles
2. **Deploy job** (needs lint)
   - setup SSH from GitHub Secret
   - create temporary vault password file
   - run `playbooks/deploy_python.yml`
   - verify with `curl` (`/` and `/health`)

Path filters configured to avoid unnecessary runs and ignore docs updates.

### GitHub Secrets used
- `ANSIBLE_VAULT_PASSWORD`
- `SSH_PRIVATE_KEY`
- `VM_HOST`
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

### README badges
Added in `README.md`:
- Python Ansible deployment workflow badge

---

## 6. Testing Results (Execution Plan + Verification)

### Provisioning/tag checks
```bash
cd ansible
ansible-playbook playbooks/provision.yml --list-tags
ansible-playbook playbooks/provision.yml --tags "docker"
ansible-playbook playbooks/provision.yml --tags "docker_install"
ansible-playbook playbooks/provision.yml --tags "packages"
```

### Compose deployment/idempotency checks
```bash
ansible-playbook playbooks/deploy.yml --ask-vault-pass
ansible-playbook playbooks/deploy.yml --ask-vault-pass
ansible webservers -a "docker ps --format '{{.Names}} {{.Image}} {{.Ports}}'"
curl -s http://31.56.228.103:5000/health
```

### Wipe checks
```bash
ansible-playbook playbooks/deploy_python.yml -e "web_app_wipe=true" --tags web_app_wipe
```

### CI/CD checks
- Push change in `ansible/vars/app_python.yml` → `ansible-deploy.yml` should run.
- Push change in `ansible/roles/web_app/**` → `ansible-deploy.yml` should run.

---

## 7. Challenges & Solutions

- **No Ansible binary in current local PowerShell/WSL during editing:**
  - mitigated by implementing complete declarative code + CI-based lint/deploy validation in workflows.
- **Compose migration complexity from single-container module to project model:**
  - resolved using `docker_compose_v2` + template-driven compose file.
- **Safe destructive operations requirement:**
  - solved with double-gated wipe mechanism (`web_app_wipe` variable + `web_app_wipe` tag).

---

## 8. Research Answers

### Task 1 (Blocks & Tags)
1. **What if `rescue` also fails?**
   - The play fails for that host after rescue attempts; `always` still executes.
2. **Can blocks be nested?**
   - Yes, nested blocks are valid and useful for grouped control flow.
3. **How do tags inherit in blocks?**
   - Tags on a block apply to tasks inside it; role/play tags also propagate.

### Task 2 (Compose)
1. **`restart: always` vs `unless-stopped`**
   - `always`: container restarts even after manual stop and daemon reboot.
   - `unless-stopped`: restarts on failures/reboot, but respects manual stop.
2. **Compose networks vs default bridge**
   - Compose creates project-scoped networks with deterministic service DNS; bridge is generic and less structured.
3. **Can Vault variables be used in templates?**
   - Yes, vaulted vars are decrypted at runtime and can be injected into Jinja templates.

### Task 3 (Wipe logic)
1. **Why variable + tag?**
   - Dual safety: variable authorizes destructive intent; tag enables selective wipe-only execution.
2. **Difference from `never` tag?**
   - `never` forces explicit tag always; variable+tag supports both wipe-only and clean reinstall flows.
3. **Why wipe before deploy?**
   - Guarantees clean state for deterministic reinstallation.
4. **When clean reinstall vs rolling update?**
   - Clean reinstall for corrupted drift/major config changes; rolling updates for minimal downtime.
5. **How to wipe images/volumes too?**
   - Extend compose down options (`remove_images`, volume removal) and add gated tasks for image/volume prune.

### Task 4 (CI/CD)
1. **Security of SSH keys in GitHub Secrets**
   - Keys are encrypted at rest, but exposure risk remains in misconfigured logs/steps; use least privilege and rotation.
2. **Staging → production pipeline**
   - Separate environments, protected branches, manual approval gate before production job.
3. **Rollback strategy**
   - Deploy immutable image tags, keep previous tag, add rollback workflow dispatch input for target tag.
4. **Why self-hosted can improve security**
   - No external runner needs direct infra access; network boundary and credentials remain inside your environment.

---

## 9. Summary

Lab 06 implementation is completed in repository code:
- Blocks/rescue/always/tags added to provisioning roles.
- Deployment migrated from container task model to Docker Compose role.
- Safe wipe logic with variable + tag control implemented.
- CI/CD automation added with lint + deploy + runtime verification.

Total deliverable status: **Main tasks complete**.
