# Lab 16 - Kubernetes Monitoring and Init Containers Report

Completed on local Kind cluster `devops-lab13`.

## 1. Kube-Prometheus Stack Components (Task 1)

- Prometheus Operator: Manages Prometheus/Alertmanager via CRDs (ServiceMonitor, Prometheus, Alertmanager).
- Prometheus: Scrapes metrics and stores time series data.
- Alertmanager: Deduplicates, groups, and routes alerts.
- Grafana: Dashboard UI for visualizing metrics.
- kube-state-metrics: Exposes Kubernetes object state as metrics.
- node-exporter: Exposes node-level CPU, memory, disk, and network metrics.

## 2. Installation Evidence (Task 1)

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

Pods and services:

```text
NAME                                                     READY   STATUS    AGE
alertmanager-monitoring-kube-prometheus-alertmanager-0   2/2     Running   11m
monitoring-grafana-789c56bf8-n7pbk                       3/3     Running   11m
monitoring-kube-prometheus-operator-f5cd8569b-prll7      1/1     Running   11m
monitoring-kube-state-metrics-5746795bd9-pcn4w           1/1     Running   11m
monitoring-prometheus-node-exporter-jsjg4                1/1     Running   11m
prometheus-monitoring-kube-prometheus-prometheus-0       2/2     Running   11m

NAME                                      TYPE        CLUSTER-IP      PORT(S)                      AGE
monitoring-grafana                        ClusterIP   10.96.79.241    80/TCP                       11m
monitoring-kube-prometheus-alertmanager   ClusterIP   10.96.17.119    9093/TCP,8080/TCP            11m
monitoring-kube-prometheus-operator       ClusterIP   10.96.50.44     443/TCP                      11m
monitoring-kube-prometheus-prometheus     ClusterIP   10.96.212.138   9090/TCP,8080/TCP            11m
monitoring-kube-state-metrics             ClusterIP   10.96.80.17     8080/TCP                     11m
monitoring-prometheus-node-exporter       ClusterIP   10.96.249.75    9100/TCP                     11m
```

## 3. Grafana Dashboard Answers (Task 2)

Grafana access:

```bash
kubectl port-forward svc/monitoring-grafana -n monitoring 3000:80
# admin / prom-operator
```

Dashboards used:
- Kubernetes / Compute Resources / Namespace (Pods)
- Kubernetes / Compute Resources / Pod
- Node Exporter / Nodes
- Kubernetes / Kubelet

Results (confirmed via Prometheus API queries):

1) Pod resources for StatefulSet (`lab16-devops-app`):
- CPU total: ~0.00175 cores (1.75m)
- Memory total: ~90,734,592 bytes (~86.6 MiB)
- Per pod CPU (cores):
  - `lab16-devops-app-0`: 0.00057
  - `lab16-devops-app-1`: 0.00063
  - `lab16-devops-app-2`: 0.00055

2) Namespace analysis (default):
- `kubectl get pods -n default` -> no pods
- CPU usage: no data (0 pods)

3) Node metrics:
- Node memory usage: 85.86% (~6470.60 MiB)
- CPU cores: 16

4) Kubelet pods/containers managed:
- Pods: 50 (from `kube_pod_info`)
- Containers: 54 (from `kube_pod_container_info`)

5) Network traffic for default namespace:
- RX/TX: no data (0 pods)

6) Alerts:
- Active alerts in Alertmanager: 2

Screenshots:
- `k8s/screenshots/10-grafana-namespace-pods.png` — Lab16 namespace dashboard showing pod CPU/memory for StatefulSet
- `k8s/screenshots/13-grafana-pod-resources.png` — Pod detail dashboard for lab16-devops-app-0
- `k8s/screenshots/11-grafana-node-exporter.png` — Node exporter dashboard showing node memory/CPU
- `k8s/screenshots/12-alertmanager-alerts.png` — Alertmanager UI showing 7 total active alerts

## 4. Init Containers (Task 3)

### 4.1 Download init container

Manifest: `k8s/init-download.yaml`

```yaml
initContainers:
  - name: init-download
    image: busybox:1.36
    command: ["sh", "-c", "wget -qO /work-dir/index.html https://example.com"]
```

Verification:

```bash
kubectl logs -n lab16 <pod> -c init-download
kubectl exec -n lab16 <pod> -- head -n 5 /usr/share/nginx/html/index.html
```

Output excerpt:

```text
wget: note: TLS certificate validation not implemented
<!doctype html><html lang="en"><head><title>Example Domain</title>...
```

### 4.2 Wait-for-service pattern

Manifest: `k8s/init-wait.yaml`

```yaml
initContainers:
  - name: wait-for-service
    image: busybox:1.36
    command:
      - sh
      - -c
      - until wget -qO- http://wait-service; do echo waiting for wait-service; sleep 2; done
```

Verification:

```bash
kubectl logs -n lab16 <wait-client-pod> -c wait-for-service
```

Output excerpt:

```text
waiting for wait-service
wget: can't connect to remote host ... Connection refused
...
<!DOCTYPE html>
<title>Welcome to nginx!</title>
```

## 5. Bonus - ServiceMonitor and Custom Metrics (2.5 pts)

ServiceMonitor template:
- `k8s/devops-app/templates/servicemonitor.yaml`

Values:
- `k8s/devops-app/values-monitoring.yaml`

Deployed ServiceMonitor:

```bash
kubectl get servicemonitor -n lab16
```

Metrics verified in Prometheus:

```text
__name__ = devops_info_endpoint_calls_total
namespace = lab16
service = lab16-devops-app
```

Prometheus access:

```bash
kubectl port-forward svc/monitoring-kube-prometheus-prometheus -n monitoring 9090:9090
```

## 6. Checklist Mapping

- ✅ Kube-Prometheus stack installed and verified
- ✅ Grafana dashboard questions answered (6/6)
  - Pod resources (lab16 StatefulSet): CPU 0.00175 cores, Memory 90.7 MiB
  - Namespace analysis (default): 0 pods, no data
  - Node metrics: 85.86% memory used, 16 CPU cores
  - Kubelet: 50 pods, 54 containers
  - Network traffic (default): 0 pods, no data
  - Active alerts: 2 (in Alertmanager UI: 7 total)
- ✅ Init container download pattern verified (file downloaded via wget)
- ✅ Init container wait-for-service pattern verified (polls until target ready)
- ✅ ServiceMonitor created and metrics scraped (devops_info_endpoint_calls_total)
- ✅ Screenshots captured (4 dashboards + Alertmanager)
- ✅ `k8s/MONITORING.md` completed
