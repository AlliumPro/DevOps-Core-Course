# Lab 13 - GitOps with ArgoCD Report

> Completed on 23 Apr 2026 on the local `kind-devops-lab13` cluster. ArgoCD is installed via Helm, applications are managed declaratively from `k8s/argocd/`, and dev/prod environments were validated together with self-healing behavior.

---

## 1. Environment and Result Summary

| Item | Value |
| --- | --- |
| Kubernetes context | `kind-devops-lab13` |
| ArgoCD install method | Helm chart `argo/argo-cd` |
| Helm release | `argocd` in namespace `argocd` |
| ArgoCD version | `v3.3.8` |
| Helm chart version | `argo-cd-9.5.4` |
| Git source | `https://github.com/AlliumPro/DevOps-Core-Course.git` |
| Tracked branch | `lab13` |
| Main app namespace | `lab13` |
| Multi-env namespaces | `dev`, `prod` |
| Bonus namespaces | `dev-appset`, `prod-appset` |

Final validated state:

```text
argocd/devops-app-main        -> Synced / Healthy / Manual
argocd/devops-app-dev         -> Synced / Healthy / Auto-Prune + SelfHeal
argocd/devops-app-prod        -> Synced / Healthy / Manual
argocd/devops-app-dev-generated   -> Synced / Healthy / Auto-Prune
argocd/devops-app-prod-generated  -> Synced / Healthy / Manual
```

---

## 2. ArgoCD Installation and Access

### 2.1 Helm installation

Repository and installation commands:

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
kubectl create namespace argocd
helm install argocd argo/argo-cd -n argocd -f k8s/argocd/values-install.yaml
```

In the current lab workspace the release was finalized with:

```bash
helm upgrade argocd argo/argo-cd -n argocd -f k8s/argocd/values-install.yaml --wait --timeout 10m
```

Implementation note:
- `k8s/argocd/values-install.yaml` increases `repoServer` probe tolerances and adds explicit resource requests/limits.
- This was necessary because the default `repo-server` liveness probe was too aggressive for the local Kind setup after Docker engine restarts.
- I also set:
  - `timeout.reconciliation: 180s`
  - `timeout.reconciliation.jitter: 30s`

Verification:

```bash
kubectl get pods -n argocd
helm list -n argocd
```

Observed stable components:
- `argocd-application-controller`
- `argocd-applicationset-controller`
- `argocd-dex-server`
- `argocd-notifications-controller`
- `argocd-redis`
- `argocd-repo-server`
- `argocd-server`

### 2.2 UI access

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

Login:
- URL: `https://127.0.0.1:8080`
- Username: `admin`
- Password: retrieved from `argocd-initial-admin-secret`

Screenshots:
- Applications overview: `k8s/screenshots/6-argocd-applications.png`
- Dev application details: `k8s/screenshots/7-argocd-dev-details.png`
- Prod application details: `k8s/screenshots/8-argocd-prod-details.png`

### 2.3 CLI access

```bash
argocd login localhost:8080 --username admin --password <decoded-password> --insecure
argocd app list
argocd app get devops-app-dev
```

CLI verification confirmed that the cluster connection works and the applications are visible to ArgoCD.

---

## 3. Declarative Application Manifests

All declarative GitOps manifests live in `k8s/argocd/`:

- `application.yaml`
- `application-dev.yaml`
- `application-prod.yaml`
- `applicationset.yaml`
- `values-install.yaml`

### 3.1 Base application (`application.yaml`)

File:
- `k8s/argocd/application.yaml`

Purpose:
- first manual ArgoCD-managed deployment into namespace `lab13`
- uses the Helm chart at `k8s/devops-app`
- uses `values.yaml`

Important fields:
- `repoURL: https://github.com/AlliumPro/DevOps-Core-Course.git`
- `targetRevision: lab13`
- `path: k8s/devops-app`
- destination namespace: `lab13`
- sync policy: manual

Why `values.yaml` instead of `values-dev.yaml`:
- the earlier dev values reused `nodePort: 30081`
- that conflicted with the dev environment service
- switching the base application to `values.yaml` resolved the collision and allowed the manual app to become `Synced/Healthy`

### 3.2 Dev application (`application-dev.yaml`)

File:
- `k8s/argocd/application-dev.yaml`

Purpose:
- development environment with automatic sync

Behavior:
- namespace `dev`
- values file `values-dev.yaml`
- automated sync enabled
- `prune: true`
- `selfHeal: true`

### 3.3 Prod application (`application-prod.yaml`)

File:
- `k8s/argocd/application-prod.yaml`

Purpose:
- production environment with manual sync only

Behavior:
- namespace `prod`
- values file `values-prod.yaml`
- manual sync

Additional local-Kind adaptation:
- `service.type=NodePort`
- `service.nodePort=30082`

I applied this override because a plain `LoadBalancer` service on Kind remains pending without an external load balancer controller, which kept ArgoCD health in `Progressing`. Using a dedicated NodePort preserved the environment separation while making the production application fully healthy in the local lab cluster.

---

## 4. Multi-Environment Deployment

Namespaces used:

```bash
kubectl get ns
```

Relevant namespaces:
- `dev`
- `prod`
- `lab13`
- `dev-appset`
- `prod-appset`

### 4.1 Dev vs Prod differences

| Setting | Dev | Prod |
| --- | --- | --- |
| Values file | `values-dev.yaml` | `values-prod.yaml` |
| Replica count | `1` | `3` |
| App environment | `development` | `production` |
| CPU request | `50m` | `200m` |
| Memory request | `64Mi` | `256Mi` |
| CPU limit | `100m` | `500m` |
| Memory limit | `128Mi` | `512Mi` |
| Service exposure | NodePort `30081` | NodePort `30082` |
| Sync policy | Auto-sync + self-heal + prune | Manual |

### 4.2 Why dev is automatic and prod is manual

Dev:
- faster feedback loop
- changes are applied automatically from the Git source
- self-healing is useful for frequent experimentation

Prod:
- sync is an explicit release step
- operator review remains in the loop
- this matches safer production change control

### 4.3 Validated live state

```bash
argocd app list
kubectl get pods -n dev
kubectl get pods -n prod
kubectl get pods -n lab13
```

Validated application state:
- `devops-app-dev` -> `Synced / Healthy`
- `devops-app-main` -> `Synced / Healthy`
- `devops-app-prod` -> `Synced / Healthy`

Service exposure in the lab cluster:
- `lab13` -> NodePort `30080`
- `dev` -> NodePort `30081`
- `prod` -> NodePort `30082`

Health endpoint verification was performed through port-forwarded services:

```bash
curl http://127.0.0.1:18080/health
curl http://127.0.0.1:18081/health
curl http://127.0.0.1:18082/health
```

Observed result for all three environments:

```json
{"status":"healthy", "...":"..."}
```

---

## 5. Sync Workflow and Operational Notes

### 5.1 Manual sync

Used for `devops-app-main` and `devops-app-prod`:

```bash
argocd app sync devops-app-main
argocd app sync devops-app-prod
```

Observed result:
- both applications completed with `Sync Status: Synced`
- both applications reached `Health Status: Healthy`

### 5.2 Auto-sync behavior

`devops-app-dev` is configured with:

```yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
```

Meaning:
- Git changes or live drift can trigger reconciliation automatically
- deleted Git-managed resources may be pruned
- live drift is reverted automatically

### 5.3 Polling interval and triggers

Official ArgoCD docs state that:
- Git polling defaults to `120s` plus up to `60s` jitter
- `selfHeal` retries after a 5-second timeout by default

Official references:
- <https://argo-cd.readthedocs.io/en/latest/faq/>
- <https://argo-cd.readthedocs.io/en/latest/user-guide/auto_sync/>

In this lab installation I changed the polling settings to:

```yaml
configs:
  cm:
    timeout.reconciliation: 180s
    timeout.reconciliation.jitter: 30s
```

So in this cluster:
- Git polling is configured for roughly `180-210s`
- live-cluster self-heal on the dev app was observed in practice in about 5-6 seconds

---

## 6. Self-Healing and Drift Tests

All self-healing experiments were executed against the `devops-app-dev` application because it is the environment with `automated + selfHeal + prune`.

### 6.1 Manual scale drift

Command:

```bash
kubectl scale deployment devops-app-dev-devops-app -n dev --replicas=5
```

Observed timeline:

```text
2026-04-23T21:22:40+03:00 before scale replicas=1/1
2026-04-23T21:22:40+03:00 manual scale requested -> 5
2026-04-23T21:22:46+03:00 replicas=1/1 sync=OutOfSync health=Progressing
2026-04-23T21:23:04+03:00 replicas=1/1 sync=Synced health=Healthy
```

Conclusion:
- manual scaling changed the live cluster state
- ArgoCD detected the deployment drift
- because `selfHeal: true` is enabled, ArgoCD reverted the replica count back to the Git-defined value `1`

### 6.2 Pod deletion test

Command:

```bash
kubectl delete pod -n dev -l app.kubernetes.io/instance=devops-app-dev
```

Observed timeline:

```text
2026-04-23T21:23:40+03:00 before delete pod=devops-app-dev-devops-app-5bc77b676-vk4zl
2026-04-23T21:24:11+03:00 deleted pod=devops-app-dev-devops-app-5bc77b676-vk4zl
2026-04-23T21:24:15+03:00 pods=devops-app-dev-devops-app-5bc77b676-jct69:Running ready=True
```

Conclusion:
- the pod was recreated immediately
- this is Kubernetes deployment/replicaset behavior
- ArgoCD was not needed here because the declarative deployment still matched Git

### 6.3 Configuration drift test

Manual drift:

```bash
kubectl patch deployment devops-app-dev-devops-app -n dev --type merge -p '{"spec":{"template":{"metadata":{"labels":{"manual-drift":"true"}}}}}'
```

Observed timeline:

```text
2026-04-23T21:26:59+03:00 before templateLabel=<absent>
2026-04-23T21:26:59+03:00 manual template label applied
2026-04-23T21:27:04+03:00 templateLabel=<absent> sync=Synced health=Healthy
```

Conclusion:
- modifying the pod template introduced real configuration drift
- ArgoCD self-healed the deployment and removed the unmanaged label
- this confirms the difference between:
  - Kubernetes healing failed pods
  - ArgoCD healing configuration drift

---

## 7. Bonus - ApplicationSet

### 7.1 Implementation

File:
- `k8s/argocd/applicationset.yaml`

Pattern used:
- List generator
- one template
- two generated applications

Generated applications:
- `devops-app-dev-generated`
- `devops-app-prod-generated`

Generated namespaces:
- `dev-appset`
- `prod-appset`

Extra NodePorts to avoid collisions with the main lab environments:
- `30083`
- `30084`

### 7.2 Why separate namespaces were used

I intentionally generated the ApplicationSet applications into `dev-appset` and `prod-appset` instead of reusing `dev` and `prod`:
- this avoids ownership conflicts with the individually defined applications
- it allows the bonus task to be validated live without breaking the base lab deliverables
- it still demonstrates the same multi-environment pattern from one template

### 7.3 Validation

Commands:

```bash
kubectl apply -f k8s/argocd/applicationset.yaml
argocd app sync devops-app-prod-generated
argocd app list
```

Observed healthy state:
- `devops-app-dev-generated` -> `Synced / Healthy`
- `devops-app-prod-generated` -> `Synced / Healthy`

Pods:

```bash
kubectl get pods -n dev-appset
kubectl get pods -n prod-appset
```

Screenshot:
- `k8s/screenshots/9-argocd-applicationset-generated.png`

### 7.4 When ApplicationSet is better than individual Application objects

Use individual `Application` resources when:
- the number of apps is small
- each app needs explicit hand-tuned configuration
- separate ownership or review is preferred

Use `ApplicationSet` when:
- the same app pattern repeats across environments
- many applications must be generated from structured parameters
- naming, namespaces, value files, and destinations should be standardized

Generator choice:
- **List generator**: best for a small explicit set of environments
- **Git generator**: best when folders/files should drive app discovery
- **Matrix/Merge**: best for combining environment, cluster, or tenant dimensions at scale

---

## 8. Files Added or Updated

Created:
- `k8s/argocd/application.yaml`
- `k8s/argocd/application-dev.yaml`
- `k8s/argocd/application-prod.yaml`
- `k8s/argocd/applicationset.yaml`
- `k8s/argocd/values-install.yaml`
- `k8s/ARGOCD.md`

Updated:
- `k8s/devops-app/values-prod.yaml`

Screenshots:
- `k8s/screenshots/6-argocd-applications.png`
- `k8s/screenshots/7-argocd-dev-details.png`
- `k8s/screenshots/8-argocd-prod-details.png`
- `k8s/screenshots/9-argocd-applicationset-generated.png`

---

## 9. Final Checklist

### Core lab
- [x] ArgoCD installed via Helm
- [x] All ArgoCD pods running
- [x] UI access verified via port-forward
- [x] Admin password retrieved
- [x] CLI login verified
- [x] `k8s/argocd/` manifests created
- [x] Manual application synced and verified
- [x] Dev/prod environments deployed with different config
- [x] Dev auto-sync + self-heal validated
- [x] Prod manual sync validated
- [x] Manual scale drift test documented
- [x] Pod deletion behavior documented
- [x] Configuration drift self-heal documented
- [x] Report completed in `k8s/ARGOCD.md`

### Bonus
- [x] ApplicationSet manifest created
- [x] Multiple applications generated from one template
- [x] Generator pattern documented
- [x] Generated applications validated and screenshot captured

---

## 10. Conclusion

Lab 13 is completed end-to-end:
- ArgoCD is installed and stable in the Kind cluster
- the Helm application is managed declaratively from Git-defined sources
- manual and automatic sync flows are both demonstrated
- dev and prod environments are separated and validated
- self-healing behavior is proven with real drift experiments
- the bonus ApplicationSet pattern is implemented and validated live
