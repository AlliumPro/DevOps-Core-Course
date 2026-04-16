# LAB12 - ConfigMaps and Persistent Volumes

## Environment

- Kubernetes: `kind` cluster `devops-lab12` (v1.33.1)
- Helm: v4.1.3
- Namespace: `lab12`
- App image: `devops-app:lab12-local`

## 1. Application Changes (Task 1)

### 1.1 Visits counter implementation

Implemented in `app_python/app.py`:

- Added persistent counter file path via `VISITS_FILE` (`/data/visits` by default)
- Added thread-safe file operations with process lock (`RLock`)
- Added atomic write using temp file + `os.replace`
- Root endpoint `/` now increments counter and returns `visits_count`
- Added new endpoint `/visits` that returns current persisted value without increment

Core functions:

- `get_visits_file_path()`
- `_read_visits_unlocked()`
- `_write_visits_unlocked()`
- `read_visits_count()`
- `increment_visits_count()`

### 1.2 Tests

Updated `app_python/tests/test_app.py`:

- Fixture now sets test-specific `VISITS_FILE` under `tmp_path`
- Added test `test_visits_endpoint_and_file_persistence`

Test result:

```text
.\.venv\Scripts\python.exe -m pytest -q
.......                                                                  [100%]
```

### 1.3 Local Docker persistence evidence

Created `app_python/docker-compose.yml` with bind mount:

- `./data:/data`
- `VISITS_FILE=/data/visits`

Validation:

```text
local_visits_before=2
local_visits_after_hit=3
3
local_visits_after_restart_check=3
3
```

Meaning:

- Counter increased after request (`2 -> 3`)
- File `app_python/data/visits` stored value `3`
- After container restart, `/visits` still returned `3`

`app_python/README.md` updated with `/visits`, `VISITS_FILE`, and compose persistence workflow.

## 2. ConfigMap Implementation (Task 2)

### 2.1 File-based ConfigMap

Created `k8s/devops-app/files/config.json`:

```json
{
  "applicationName": "devops-info-service",
  "environment": "development",
  "featureFlags": {
    "visitsEndpoint": true,
    "metricsEnabled": true,
    "structuredLogging": true
  },
  "settings": {
    "configVersion": "lab12",
    "owner": "devops-core-course"
  }
}
```

Created `k8s/devops-app/templates/configmap.yaml`:

- First ConfigMap renders file content using `.Files.Get "files/config.json"`
- Mounted by Deployment at `/config`

### 2.2 Env-based ConfigMap

Same template also defines second ConfigMap from values map:

- Source values: `.Values.configMap.env.data`
- Injected via `envFrom.configMapRef`

### 2.3 Deployment wiring

Updated `k8s/devops-app/templates/deployment.yaml`:

- `volumes` + `volumeMounts` for file ConfigMap (`/config`)
- `envFrom` for ConfigMap env keys
- Checksum annotations:
  - `checksum/config-file`
  - `checksum/config-env`

### 2.4 Verification outputs

```text
kubectl get configmap,pvc -n lab12

NAME                                    DATA   AGE
configmap/kube-root-ca.crt              1      32m
configmap/lab12-app-devops-app-config   1      32m
configmap/lab12-app-devops-app-env      3      32m

NAME                                              STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
persistentvolumeclaim/lab12-app-devops-app-data   Bound    pvc-5d9d24dc-9feb-47a1-bef1-22082a731ed3   100Mi      RWO            standard       32m
```

```text
kubectl exec -n lab12 <pod> -- cat /config/config.json

{
  "applicationName": "devops-info-service",
  "environment": "development",
  "featureFlags": {
    "visitsEndpoint": true,
    "metricsEnabled": true,
    "structuredLogging": true
  },
  "settings": {
    "configVersion": "lab12",
    "owner": "devops-core-course"
  }
}
```

```text
kubectl exec -n lab12 <pod> -- env | grep -E '^(APP_|FEATURE_|VISITS_FILE|PORT|LOG_LEVEL)'

APP_ENV=development
APP_PROFILE=development
FEATURE_METRICS_ENABLED=true
FEATURE_VISITS_ENABLED=true
LOG_LEVEL=INFO
PORT=5000
VISITS_FILE=/data/visits
```

## 3. Persistent Volume Implementation (Task 3)

### 3.1 PVC template

Created `k8s/devops-app/templates/pvc.yaml`:

- Kind: `PersistentVolumeClaim`
- Access mode: `ReadWriteOnce`
- Requested size: `100Mi` (from values)
- Optional storage class via `persistence.storageClass`
- Supports existing claim via `persistence.existingClaim`

Values structure in `k8s/devops-app/values.yaml`:

```yaml
persistence:
  enabled: true
  existingClaim: ""
  mountPath: /data
  fileName: visits
  accessMode: ReadWriteOnce
  size: 100Mi
  storageClass: ""
```

### 3.2 Deployment mount

In Deployment:

- Volume: `persistentVolumeClaim.claimName: <release>-devops-app-data`
- Mount path: `/data`
- App variable: `VISITS_FILE=/data/visits`

### 3.3 Persistence proof (pod recreation)

```text
persistence_before=2
persistence_after_hits=4
visits_file_before_delete=4
kubectl delete pod ...
persistence_pod_after=lab12-app-devops-app-8587d6c494-dr8mw
visits_file_after_recreate=4
persistence_after_recreate=4
```

Result: counter value survived pod deletion and recreation because visits file is stored on PVC.

## 4. ConfigMap vs Secret (Task 4)

When to use ConfigMap:

- Non-sensitive configuration
- Feature flags, app mode, service settings
- Files and environment values that can be visible to regular operators

When to use Secret:

- Sensitive values (passwords, tokens, API keys, certificates)
- Credentials that must be controlled by tighter RBAC and rotation process

Key differences:

- Data sensitivity: ConfigMap (plain config) vs Secret (sensitive data)
- Intended usage: ConfigMap for app config, Secret for confidential material
- Encoding: Secret data is base64-encoded by API schema (not encryption by itself)

## 5. Bonus — ConfigMap Hot Reload

### 5.1 Default mounted-file update behavior

Patched ConfigMap and measured delay until mounted file changed in running pod.

Observed evidence:

```text
configmap/lab12-app-devops-app-config patched
config_reload_seen=True
config_reload_poll_attempts=270
config_reload_elapsed_seconds=53.11
```

This demonstrates non-instant propagation. In Kubernetes, mounted ConfigMap refresh depends on kubelet sync/cache cycle.

### 5.2 subPath limitation demonstration

Created temporary demo pod with `subPath` mount for single file and patched ConfigMap value from `v1` to `v2`.

Observed evidence:

```text
subpath_before=version=v1
configmap/subpath-demo-cm patched
subpath_updated=False
subpath_poll_attempts=301
subpath_elapsed_seconds=57.92
subpath_after=version=v1
configmap_value=version=v2
```

Conclusion: `subPath` file mount did not receive live updates even though ConfigMap object changed.

### 5.3 Reload strategy implemented: checksum annotations + Helm upgrade

Implemented in Deployment template:

- `checksum/config-file: {{ .Files.Get "files/config.json" | sha256sum }}`
- `checksum/config-env: {{ toYaml .Values.configMap.env.data | sha256sum }}`

Demonstration (env ConfigMap change):

```text
pod_before=lab12-app-devops-app-8587d6c494-zkh6s
checksum_env_before=4d3564b5727ff17f048ad7e685984e59000984daa5c9eae27331c9b47b6bba18
...
pod_after=lab12-app-devops-app-676c9bbfb4-cc7w2
checksum_env_after=366795daedfd88a47d32395f7e0e1cbf8997dd9abc6b05f888d170e0d7ad2b71
APP_PROFILE=development-v2
```

Result: changing ConfigMap source values changed checksum annotation, which triggered pod rollout.

## 6. Helm/Chart Validation

Chart checks:

```text
helm lint k8s/devops-app
1 chart(s) linted, 0 chart(s) failed
```

Template render includes required resources:

- ConfigMap (file)
- ConfigMap (env)
- PVC
- Deployment with checksum annotations
- `VISITS_FILE=/data/visits`

Release status:

```text
helm list -n lab12
lab12-app   deployed   devops-app-0.1.0
```

## 7. Summary

Lab 12 is fully implemented:

- Persistent visits counter in application and tests
- Local Docker persistence validated
- Helm ConfigMaps implemented for file and env usage
- PVC integrated and persistence across pod recreation verified
- Required documentation outputs collected
- Bonus completed:
  - measured ConfigMap update delay
  - demonstrated `subPath` update limitation
  - implemented checksum-triggered rollout pattern
