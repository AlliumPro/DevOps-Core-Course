# Lab 14 - Progressive Delivery with Argo Rollouts Report

Completed on local Kind cluster `devops-lab13`.

## 1. Argo Rollouts Setup

### 1.1 Controller and Dashboard installation

```bash
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/dashboard-install.yaml
kubectl rollout status deploy/argo-rollouts -n argo-rollouts --timeout=300s
kubectl rollout status deploy/argo-rollouts-dashboard -n argo-rollouts --timeout=300s
```

Verification:

```bash
kubectl get pods -n argo-rollouts
```

Result: both `argo-rollouts` and `argo-rollouts-dashboard` are `Running`.

### 1.2 kubectl plugin installation

```bash
Invoke-WebRequest -Uri https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-windows-amd64 -OutFile kubectl-argo-rollouts.exe
kubectl argo rollouts version
```

Result (validated): `kubectl-argo-rollouts v1.9.0`.

### 1.3 Dashboard access

```bash
kubectl port-forward svc/argo-rollouts-dashboard -n argo-rollouts 3100:3100
```

UI URL: `http://localhost:3100`

## 2. Rollout vs Deployment

Common parts:
- same Pod template structure (`spec.template`)
- same selector/replicas concepts
- same probes/resources/config

Additional Rollout capabilities:
- `strategy.canary` with step-based traffic shifting
- `strategy.blueGreen` with active/preview service cutover
- `promote`, `abort`, `undo` operational controls
- analysis integration (`AnalysisTemplate`) for automated checks and rollback decisions

## 3. Helm Chart Changes

Chart: `k8s/devops-app`

Implemented:
- `templates/rollout.yaml` (new Rollout resource)
- `templates/service-canary-stable.yaml` (canary stable service)
- `templates/service-canary-canary.yaml` (canary canary service)
- `templates/service-bluegreen-active.yaml` (blue-green active service)
- `templates/service-bluegreen-preview.yaml` (blue-green preview service)
- `templates/analysis-template.yaml` (bonus AnalysisTemplate)
- `templates/deployment.yaml` kept behind `if not .Values.rollout.enabled`

Values added:
- `rollout.enabled`
- `rollout.strategy` (`canary` or `blueGreen`)
- canary steps (20% -> pause -> 40% -> 60% -> 80% -> 100%)
- blue-green active/preview service names and promotion mode

Lab-specific values files:
- `k8s/devops-app/values-canary.yaml`
- `k8s/devops-app/values-bluegreen.yaml`

## 4. Canary Deployment (Task 2)

Namespace: `lab14-canary`

### 4.1 Baseline deploy

```bash
kubectl create ns lab14-canary
helm install lab14-canary k8s/devops-app -n lab14-canary -f k8s/devops-app/values-canary.yaml --wait --timeout 10m
kubectl argo rollouts get rollout lab14-canary-devops-app -n lab14-canary
```

Validated baseline: `Healthy`, 4/4 ready.

### 4.2 Trigger rollout change

To avoid Helm ownership conflict on service selectors (controller updates selector hashes), rollout revisions were triggered with Argo CLI:

```bash
docker tag devops-app:lab13-local devops-app:lab14-v2
kind load docker-image devops-app:lab14-v2 --name devops-lab13
kubectl argo rollouts set image lab14-canary-devops-app devops-app=devops-app:lab14-v2 -n lab14-canary
```

Observed:
- first pause at step `1/9` (`CanaryPauseStep`) required manual promotion
- after manual promotion, timed pauses progressed automatically
- final state reached `Healthy`, step `9/9`, stable image switched to `devops-app:lab14-v2`

### 4.3 Manual promotion demonstration

```bash
kubectl argo rollouts promote lab14-canary-devops-app -n lab14-canary
kubectl argo rollouts status lab14-canary-devops-app -n lab14-canary --timeout 180s
```

Status progression observed in CLI:
- `Paused - CanaryPauseStep`
- `Progressing - more replicas need to be updated`
- `Progressing - old replicas are pending termination`
- `Healthy`

### 4.4 Abort / rollback demonstration

```bash
kubectl argo rollouts abort lab14-canary-devops-app -n lab14-canary
kubectl argo rollouts get rollout lab14-canary-devops-app -n lab14-canary
```

Observed rollback behavior:
- canary ReplicaSet scaled to 0
- stable ReplicaSet remained serving traffic
- status showed `RolloutAborted`

## 5. Blue-Green Deployment (Task 3)

Namespace: `lab14-bluegreen`

### 5.1 Baseline deploy

```bash
kubectl create ns lab14-bluegreen
helm install lab14-bluegreen k8s/devops-app -n lab14-bluegreen -f k8s/devops-app/values-bluegreen.yaml --wait --timeout 10m
kubectl get svc -n lab14-bluegreen
kubectl argo rollouts get rollout lab14-bluegreen-devops-app -n lab14-bluegreen
```

Created services:
- `lab14-bluegreen-devops-app-active`
- `lab14-bluegreen-devops-app-preview`

### 5.2 Preview creation and validation

```bash
docker tag devops-app:lab14-v2 devops-app:lab14-v3
kind load docker-image devops-app:lab14-v3 --name devops-lab13
kubectl argo rollouts set image lab14-bluegreen-devops-app devops-app=devops-app:lab14-v3 -n lab14-bluegreen
kubectl argo rollouts get rollout lab14-bluegreen-devops-app -n lab14-bluegreen
```

Before promotion:
- active service selector hash: old/stable
- preview service selector hash: new revision

### 5.3 Promotion and active cutover

```bash
kubectl argo rollouts promote lab14-bluegreen-devops-app -n lab14-bluegreen
kubectl argo rollouts promote lab14-bluegreen-devops-app -n lab14-bluegreen
kubectl argo rollouts status lab14-bluegreen-devops-app -n lab14-bluegreen --timeout 180s
```

After cutover:
- active service hash moved to new preview revision
- rollout became `Healthy`

### 5.4 Instant rollback after promotion

Second full cycle executed with image `devops-app:lab14-v4`.

```bash
kubectl argo rollouts undo lab14-bluegreen-devops-app -n lab14-bluegreen
kubectl argo rollouts status lab14-bluegreen-devops-app -n lab14-bluegreen --timeout 180s
```

Validated rollback:
- active service hash switched back to previous stable hash instantly
- rollout stayed `Healthy`

## 6. Bonus - Automated Analysis

Analysis integrated into canary via `templates/analysis-template.yaml` and `rollout.canary.analysis.enabled=true`.

Template behavior:
- web metric checks `/health` on canary service
- `interval: 10s`
- `count: 3`
- `failureLimit: 1`
- `successCondition: result == "healthy"`

Observed in rollout tree:
- `AnalysisRun ... Successful`
- canary continued automatically when checks passed

## 7. Strategy Comparison

Canary:
- Pros: gradual risk exposure, controlled percentage rollout
- Cons: slower delivery, more operational steps
- Best for: high-risk releases, production traffic validation

Blue-Green:
- Pros: instant cutover and instant rollback, clear preview testing
- Cons: temporary double capacity required
- Best for: fast switchovers, strict go/no-go release gates

Recommendation:
- Use canary for user-facing or risky changes where phased exposure is critical.
- Use blue-green for releases that need very fast switch and rollback with a dedicated preview stage.

## 8. Commands Reference

Most useful commands used:

```bash
# Rollout inspection
kubectl argo rollouts get rollout <name> -n <ns>
kubectl argo rollouts status <name> -n <ns> --timeout 180s

# Rollout controls
kubectl argo rollouts promote <name> -n <ns>
kubectl argo rollouts abort <name> -n <ns>
kubectl argo rollouts undo <name> -n <ns>
kubectl argo rollouts set image <name> <container>=<image:tag> -n <ns>

# Services and selectors
kubectl get svc -n <ns>
kubectl get svc <service> -n <ns> -o jsonpath='{.spec.selector}'

# Dashboard
kubectl port-forward svc/argo-rollouts-dashboard -n argo-rollouts 3100:3100
```

## 9. Checklist Mapping

Task 1:
- controller installed and running
- plugin installed and verified
- dashboard accessible
- Rollout vs Deployment differences documented

Task 2:
- Deployment converted to Rollout
- canary steps configured (20/40/60/80/100 with pauses)
- manual promotion validated
- timed automatic progression validated
- abort rollback validated

Task 3:
- blue-green strategy configured
- active/preview services configured and validated
- preview tested before cutover
- promotion to active validated
- rollback via undo validated

Task 4:
- this document (`k8s/ROLLOUTS.md`) completed with setup, behavior, comparison, and command reference

Bonus:
- AnalysisTemplate implemented and integrated
- successful analysis run observed in canary flow
