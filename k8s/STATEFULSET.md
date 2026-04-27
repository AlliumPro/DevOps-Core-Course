# Lab 15 - StatefulSet and Persistent Storage Report

Completed on local Kind cluster `devops-lab13`.

## 1. StatefulSet Overview (Task 1)

StatefulSet guarantees:
- Stable, unique pod names (`app-0`, `app-1`, `app-2`).
- Stable network identity for each pod via headless service DNS.
- Stable, persistent storage per pod (PVC per ordinal).
- Ordered, graceful updates and scaling.

Deployment vs StatefulSet:
- Deployment creates interchangeable pods with random suffixes.
- StatefulSet provides ordered identity and per-pod storage.
- Use StatefulSet for stateful workloads (databases, queues, distributed systems).

Headless service:
- `clusterIP: None` creates DNS records for each pod.
- DNS pattern: `<pod>.<headless-service>.<namespace>.svc.cluster.local`.

## 2. Implementation in Helm (Task 2)

Chart: `k8s/devops-app`

Added templates:
- `templates/statefulset.yaml`
- `templates/service-headless.yaml`

Kept external access service:
- `templates/service.yaml` remains for ClusterIP/NodePort.

StatefulSet uses `volumeClaimTemplates` for per-pod PVCs.

Values used:
- `k8s/devops-app/values-statefulset.yaml`

Key values:
- `statefulset.enabled: true`
- `rollout.enabled: false`
- `persistence.enabled: true`

## 3. Resource Verification (Task 4)

```bash
kubectl get sts -n lab15
kubectl get pods -n lab15 -o wide
kubectl get pvc -n lab15
kubectl get svc -n lab15
```

Observed resources (excerpt):

```text
NAME               READY   AGE
lab15-devops-app   3/3     45s

NAME                 READY   STATUS    AGE   IP
lab15-devops-app-0   1/1     Running   45s   10.244.0.56
lab15-devops-app-1   1/1     Running   33s   10.244.0.58
lab15-devops-app-2   1/1     Running   21s   10.244.0.60

NAME                      STATUS   CAPACITY   STORAGECLASS
data-lab15-devops-app-0   Bound    50Mi       standard
data-lab15-devops-app-1   Bound    50Mi       standard
data-lab15-devops-app-2   Bound    50Mi       standard

NAME                        TYPE        CLUSTER-IP
lab15-devops-app            ClusterIP   10.96.202.170
lab15-devops-app-headless   ClusterIP   None
```

## 4. Network Identity Test (Task 3)

```bash
kubectl exec -n lab15 lab15-devops-app-0 -- python -c "import socket; print(socket.gethostbyname('lab15-devops-app-1.lab15-devops-app-headless'))"
kubectl exec -n lab15 lab15-devops-app-0 -- python -c "import socket; print(socket.gethostbyname('lab15-devops-app-2.lab15-devops-app-headless'))"
```

Result:

```text
pod-1 10.244.0.58
pod-2 10.244.0.60
```

## 5. Per-Pod Storage Isolation (Task 3)

Each pod keeps its own visit counter in `/data/visits` (per-pod PVC).

Commands:

```bash
kubectl exec -n lab15 lab15-devops-app-0 -- python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:5000/').read(); u.urlopen('http://127.0.0.1:5000/').read(); print(u.urlopen('http://127.0.0.1:5000/visits').read().decode())"

kubectl exec -n lab15 lab15-devops-app-1 -- python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:5000/').read(); print(u.urlopen('http://127.0.0.1:5000/visits').read().decode())"

kubectl exec -n lab15 lab15-devops-app-2 -- python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:5000/').read(); u.urlopen('http://127.0.0.1:5000/').read(); u.urlopen('http://127.0.0.1:5000/').read(); print(u.urlopen('http://127.0.0.1:5000/visits').read().decode())"
```

Result:

```json
{"visits":2,"visits_file":"/data/visits"}
{"visits":1,"visits_file":"/data/visits"}
{"visits":3,"visits_file":"/data/visits"}
```

Each pod maintains its own counter, confirming isolated per-pod storage.

## 6. Persistence Test (Task 3)

```bash
kubectl exec -n lab15 lab15-devops-app-0 -- python -c "import urllib.request as u; print(u.urlopen('http://127.0.0.1:5000/visits').read().decode())"
kubectl delete pod -n lab15 lab15-devops-app-0
kubectl wait --for=condition=ready pod -n lab15 lab15-devops-app-0 --timeout=180s
kubectl exec -n lab15 lab15-devops-app-0 -- python -c "import urllib.request as u; print(u.urlopen('http://127.0.0.1:5000/visits').read().decode())"
```

Result before and after restart:

```json
{"visits":2,"visits_file":"/data/visits"}
{"visits":2,"visits_file":"/data/visits"}
```

Persistence confirmed.

## 7. Bonus: StatefulSet Update Strategies

### 7.1 Partitioned RollingUpdate

```bash
helm upgrade lab15 k8s/devops-app -n lab15 -f k8s/devops-app/values-statefulset.yaml \
  --set image.tag=lab15-v2 \
  --set statefulset.updateStrategy.type=RollingUpdate \
  --set statefulset.updateStrategy.partition=2
```

Images after update:

```text
lab15-devops-app-0 -> devops-app:lab14-v2
lab15-devops-app-1 -> devops-app:lab14-v2
lab15-devops-app-2 -> devops-app:lab15-v2
```

Only pod with ordinal >= 2 updated, as expected.

### 7.2 OnDelete Strategy

```bash
helm upgrade lab15 k8s/devops-app -n lab15 -f k8s/devops-app/values-statefulset.yaml \
  --set image.tag=lab15-v3 \
  --set statefulset.updateStrategy.type=OnDelete
```

Pods did not update until manually deleted:

```bash
kubectl delete pod -n lab15 lab15-devops-app-1
kubectl wait --for=condition=ready pod -n lab15 lab15-devops-app-1 --timeout=180s
```

Result:

```text
lab15-devops-app-1 -> devops-app:lab15-v3
```

## 8. Checklist Mapping

- StatefulSet guarantees documented
- `statefulset.yaml` created with `volumeClaimTemplates`
- Headless service created
- Per-pod PVCs verified
- DNS resolution tested
- Per-pod storage isolation demonstrated
- Persistence after pod deletion verified
- Bonus update strategies tested and documented
