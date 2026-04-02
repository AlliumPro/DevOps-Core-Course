# LAB10 - Helm Package Manager

## 1. Helm Fundamentals

### 1.1 Why Helm

Helm solves the main pain points of plain Kubernetes manifests:

- Reuse: one chart can be deployed in multiple environments.
- Configuration: values files separate code from environment settings.
- Lifecycle: install, upgrade, rollback, uninstall are first-class operations.
- Standardization: chart structure and templating are consistent across teams.

### 1.2 Installation and version

Helm was installed via `winget` and verified locally.

```powershell
winget install -e --id Helm.Helm --accept-package-agreements --accept-source-agreements
helm version
```

Observed output:

```text
version.BuildInfo{Version:"v4.1.3", ... , KubeClientVersion:"v1.35"}
```

### 1.3 Repository setup and chart exploration

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm search repo prometheus-community/prometheus
helm show chart prometheus-community/prometheus
```

Observed output excerpts:

```text
"prometheus-community" has been added to your repositories
NAME                                    CHART VERSION   APP VERSION
prometheus-community/prometheus         28.15.0         v3.11.0
```

`helm show chart` also confirmed standard chart metadata and dependency structure.

## 2. Chart Overview

Helm artifacts created in `k8s/`:

- Main application chart: `k8s/devops-app`
- Secondary application chart (bonus): `k8s/devops-app2`
- Shared library chart (bonus): `k8s/common-lib`

### 2.1 Main chart structure (`k8s/devops-app`)

Key files:

- `Chart.yaml`: chart metadata and dependency on `common-lib`.
- `values.yaml`: default configuration.
- `values-dev.yaml`: development overrides.
- `values-prod.yaml`: production overrides.
- `templates/deployment.yaml`: deployment template.
- `templates/service.yaml`: service template.
- `templates/hooks/pre-install-job.yaml`: pre-install hook.
- `templates/hooks/post-install-job.yaml`: post-install hook.
- `templates/_helpers.tpl`: chart-local helper wrappers over shared library helpers.

### 2.2 Shared template strategy

To avoid duplication, both app charts depend on `k8s/common-lib` (`type: library`) and use common helper templates:

- `common.fullname`
- `common.labels`
- `common.selectorLabels`

This keeps naming/labeling consistent and reduces maintenance overhead.

## 3. Configuration Guide

### 3.1 Important values

Main chart defaults (`k8s/devops-app/values.yaml`) include:

- `replicaCount`
- `image.repository`, `image.tag`, `image.pullPolicy`
- `service.type`, `service.port`, `service.targetPort`, `service.nodePort`
- `resources.requests/limits`
- `livenessProbe` and `readinessProbe` (kept active, never commented out)
- `env` variables
- `hooks.enabled`, `hooks.image`

### 3.2 Multi-environment values

Development (`values-dev.yaml`):

- `replicaCount: 1`
- relaxed resources
- `service.type: NodePort`
- faster probe timings

Production (`values-prod.yaml`):

- `replicaCount: 3`
- stronger requests/limits
- `service.type: LoadBalancer`
- production-like probe timings

### 3.3 Installation examples

Dev install:

```bash
helm install devops-app-release k8s/devops-app -n lab10 -f k8s/devops-app/values-dev.yaml --set image.repository=devops-app --set image.tag=lab10-local
```

Prod upgrade:

```bash
helm upgrade devops-app-release k8s/devops-app -n lab10 -f k8s/devops-app/values-prod.yaml --set image.repository=devops-app --set image.tag=lab10-local
```

## 4. Hook Implementation

Implemented hooks in the main chart:

1. Pre-install hook
- File: `templates/hooks/pre-install-job.yaml`
- Type: `pre-install`
- Weight: `-5`
- Deletion policy: `before-hook-creation,hook-succeeded`
- Purpose: lightweight pre-deploy validation/log marker.

2. Post-install hook
- File: `templates/hooks/post-install-job.yaml`
- Type: `post-install`
- Weight: `5`
- Deletion policy: `before-hook-creation,hook-succeeded`
- Purpose: smoke-check/log marker after deployment.

Execution order:

- Pre-install runs before regular resources.
- Post-install runs after install completion.
- Lower weight runs first.

Hook evidence:

```text
Normal SuccessfulCreate job/...-pre-install
Normal Completed        job/...-pre-install
Normal SuccessfulCreate job/...-post-install
Normal Completed        job/...-post-install
```

Deletion policy evidence:

```bash
kubectl get jobs -n lab10
```

Output:

```text
No resources found in lab10 namespace.
```

## 5. Installation Evidence

### 5.1 Lint, template, dry-run

```bash
helm lint k8s/devops-app
helm lint k8s/devops-app2
helm template dev10 k8s/devops-app -f k8s/devops-app/values-dev.yaml
helm install --dry-run --debug dev10 k8s/devops-app -f k8s/devops-app/values-dev.yaml
```

Observed:

```text
1 chart(s) linted, 0 chart(s) failed
```

Rendered manifest excerpt (dev):

```text
kind: Service
type: NodePort
nodePort: 30081
...
kind: Deployment
replicas: 1
```

### 5.2 Live deployment state

```bash
helm list -n lab10
kubectl get all -n lab10
```

Observed excerpts:

```text
devops-app-release   deployed   devops-app-0.1.0
devops-app2-release  deployed   devops-app2-0.1.0
```

```text
deployment.apps/devops-app-release-devops-app     1/1
service/devops-app-release-devops-app             NodePort

deployment.apps/devops-app2-release-devops-app2   2/2
service/devops-app2-release-devops-app2           ClusterIP
```

### 5.3 Environment switch evidence (dev -> prod)

After `helm upgrade` with prod values:

```text
deployment.apps/devops-app-release-devops-app   3/3
service/devops-app-release-devops-app           LoadBalancer
```

After rollback to revision 1:

```text
Rollback was a success!
deployment.apps/devops-app-release-devops-app   1/1
```

## 6. Operations

Commands used:

Install:

```bash
helm install devops-app-release k8s/devops-app -n lab10 -f k8s/devops-app/values-dev.yaml --set image.repository=devops-app --set image.tag=lab10-local
```

Upgrade:

```bash
helm upgrade devops-app-release k8s/devops-app -n lab10 -f k8s/devops-app/values-prod.yaml --set image.repository=devops-app --set image.tag=lab10-local
```

History:

```bash
helm history devops-app-release -n lab10
```

Rollback:

```bash
helm rollback devops-app-release 1 -n lab10 --wait --timeout 180s
```

Uninstall:

```bash
helm uninstall devops-app-release -n lab10
helm uninstall devops-app2-release -n lab10
```

## 7. Testing and Validation

Static validation:

- `helm lint` for both charts passed.
- `helm template` verified rendered resources.
- `helm install --dry-run --debug` verified release rendering and hooks.

Runtime validation:

- Main app endpoint was verified through port-forward:

```text
http://127.0.0.1:8082/health 200 {"status":"healthy", ...}
```

- Second app endpoint was verified:

```text
http://127.0.0.1:8083/ 200 Hello from app2
```

## 8. Bonus - Library Charts

### 8.1 Library chart implementation

Created `k8s/common-lib` as a library chart:

- `type: library` in `Chart.yaml`
- shared helper templates in `templates/_helpers.tpl`

### 8.2 Reuse in both charts

Both `k8s/devops-app/Chart.yaml` and `k8s/devops-app2/Chart.yaml` include:

```yaml
dependencies:
  - name: common-lib
    version: 0.1.0
    repository: "file://../common-lib"
```

Dependencies resolved with:

```bash
helm dependency update k8s/devops-app
helm dependency update k8s/devops-app2
```

Both charts render and install successfully using the shared template functions.

### 8.3 Benefits

- DRY: no duplicated naming/label helper logic.
- Consistency: labels/selectors follow one standard.
- Maintainability: one place to adjust common template behavior.

## 9. Final Result

Lab 10 was completed end-to-end:

- Helm 4 installed and verified.
- Public chart repositories explored.
- Kubernetes manifests converted into reusable Helm charts.
- Multi-environment deployment implemented via values files.
- Pre-install and post-install hooks implemented and validated.
- Full operation lifecycle demonstrated: install, upgrade, rollback.
- Bonus task completed with reusable library chart used by two application charts.
