# LAB11 - Kubernetes Secrets and HashiCorp Vault

## Environment

- Kubernetes: kind cluster `devops-lab11` (v1.33.1)
- Helm: v4.1.3
- Namespace for app: `lab11`
- Namespace for Vault: `vault`

## 1. Kubernetes Secrets (Task 1)

### 1.1 Secret creation via kubectl

Command:

```bash
kubectl create secret generic app-credentials -n lab11 \
  --from-literal=username=lab11-user \
  --from-literal=password=lab11-pass
```

Result:

```text
secret/app-credentials created
```

### 1.2 View YAML and decode

View:

```bash
kubectl get secret app-credentials -n lab11 -o yaml
```

Output excerpt:

```yaml
data:
  password: bGFiMTEtcGFzcw==
  username: bGFiMTEtdXNlcg==
```

Decode demonstration:

```text
username(base64)=bGFiMTEtdXNlcg==
password(base64)=bGFiMTEtcGFzcw==
username(decoded)=lab11-user
password(decoded)=lab11-pass
```

### 1.3 Encoding vs encryption

- Base64 in Kubernetes Secret is encoding, not cryptographic protection.
- Anyone with API access + read permission to secrets can decode values.
- By default, Kubernetes does not guarantee etcd encryption at rest unless explicitly configured by cluster admins.
- In production, enable etcd encryption at rest and strict RBAC; for higher security and auditability, use an external secret manager (for this lab: Vault).

## 2. Helm-Managed Secrets (Task 2)

## 2.1 Chart changes

Main chart extended in `k8s/devops-app`:

- `templates/secrets.yaml` created (K8s Secret resource with `stringData`)
- `templates/serviceaccount.yaml` created (dedicated SA for Vault auth binding)
- `templates/deployment.yaml` updated to consume secrets using `envFrom.secretRef`
- `templates/_helpers.tpl` updated with named template `devops-app.envVars`
- `values.yaml` cleaned and extended with:
  - `secret.*`
  - `serviceAccount.*`
  - `vault.*`

### 2.2 Secret template

Implemented template:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "devops-app.secretName" . }}
stringData:
  username: {{ .Values.secret.data.username | quote }}
  password: {{ .Values.secret.data.password | quote }}
```

### 2.3 Secret consumption in deployment

Implemented in pod container:

```yaml
env:
  {{- include "devops-app.envVars" . | nindent 12 }}
envFrom:
  - secretRef:
      name: {{ include "devops-app.secretName" . }}
```

### 2.4 Deployment and verification

Install command:

```bash
helm install lab11-app k8s/devops-app -n lab11 \
  -f k8s/devops-app/values-dev.yaml \
  --set image.repository=devops-app \
  --set image.tag=lab11-local \
  --set secret.data.username=helm-user \
  --set secret.data.password=helm-pass
```

Resource state excerpt:

```text
deployment.apps/lab11-app-devops-app   1/1
service/lab11-app-devops-app           NodePort 80:30081/TCP
secret/lab11-app-devops-app-secret     Opaque
```

Inside pod (`env`):

```text
username=helm-user
password=helm-pass
```

`kubectl describe pod` check:

```text
Environment Variables from:
  lab11-app-devops-app-secret  Secret  Optional: false
```

Plain secret values are not printed in `describe`; only source reference is shown.

## 3. Resource Management (Task 2 requirement)

Configured in chart values and applied in deployment:

```yaml
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "300m"
    memory: "256Mi"
```

Requests vs limits:

- Requests: minimum guaranteed resources used by scheduler.
- Limits: upper cap to prevent a pod from over-consuming node resources.

Selection rationale:

- App is lightweight Flask API, so moderate memory and low CPU are sufficient.
- Requests keep scheduling stable.
- Limits protect node stability from runaway resource usage.

## 4. Vault Integration (Task 3)

### 4.1 Vault installation via Helm

Commands:

```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update
helm install vault hashicorp/vault -n vault \
  --set "server.dev.enabled=true" \
  --set "injector.enabled=true"
```

Verification:

```text
vault-0                                1/1 Running
vault-agent-injector-...               1/1 Running
```

### 4.2 KV engine and secret creation

KV v2 already mounted at `secret/` in dev deployment. Secret written to app path:

```bash
vault kv put secret/devops-app/config \
  username="vault-user" \
  password="vault-pass" \
  api_key="vault-api-key-123"
```

Verification:

```text
Secret Path: secret/data/devops-app/config
Data:
  username: vault-user
  password: vault-pass
  api_key:  vault-api-key-123
```

### 4.3 Kubernetes auth, policy, role

Enabled and configured Kubernetes auth method in Vault.

Policy used:

```hcl
path "secret/data/devops-app/config" {
  capabilities = ["read"]
}
```

Role created:

- Role: `devops-app-role`
- Bound service account: `devops-app-sa`
- Bound namespace: `lab11`
- Policy: `devops-app-policy`

Verification excerpt:

```text
bound_service_account_names       [devops-app-sa]
bound_service_account_namespaces  [lab11]
policies                          [devops-app-policy]
```

### 4.4 Vault Agent injection enabled in chart

Deployment annotations (enabled when `vault.enabled=true`):

- `vault.hashicorp.com/agent-inject: "true"`
- `vault.hashicorp.com/role: "devops-app-role"`
- `vault.hashicorp.com/agent-inject-secret-app-config.env: "secret/data/devops-app/config"`

Release upgrade:

```bash
helm upgrade lab11-app k8s/devops-app -n lab11 \
  -f k8s/devops-app/values-dev.yaml \
  --set image.repository=devops-app \
  --set image.tag=lab11-local \
  --set secret.data.username=helm-user \
  --set secret.data.password=helm-pass \
  --set vault.enabled=true
```

Verification:

```text
pod/lab11-app-devops-app-...   2/2 Running
annotation vault.hashicorp.com/agent-inject = true
```

Injected file proof:

```text
/vault/secrets/app-config.env exists
DATABASE_USERNAME=vault-user
DATABASE_PASSWORD=vault-pass
API_KEY=vault-api-key-123
```

### 4.5 Sidecar injection pattern

What happens:

1. Mutating webhook sees Vault annotations.
2. Pod spec is mutated to include Vault agent init/sidecar.
3. Agent authenticates to Vault via Kubernetes service account JWT.
4. Agent reads permitted secret path and writes rendered file to shared volume.
5. Application reads injected file from `/vault/secrets/...`.

## 5. Security Analysis (Task 4)

### Kubernetes Secrets vs Vault

Kubernetes Secrets:

- Pros: native, simple, no extra components.
- Cons: base64 only, depends on cluster-level etcd encryption/RBAC, limited secret lifecycle controls.

Vault:

- Pros: centralized secret management, policy-based access, detailed auditing, dynamic secrets, rotation patterns, strong auth methods.
- Cons: additional operational complexity and components.

### When to use what

Use K8s Secrets when:

- environment is simple,
- security requirements are moderate,
- secret lifecycle is straightforward.

Use Vault when:

- multiple apps/environments share secret workflows,
- strict security/audit controls are required,
- rotation and policy-driven access are needed.

### Production recommendations

1. Enable etcd encryption at rest.
2. Enforce least-privilege RBAC for secret access.
3. Use external secret manager (Vault) for sensitive/critical data.
4. Avoid storing real secrets in Git; pass via CI/CD or runtime secret managers.
5. Enable auditing and rotation strategy.

## 6. Bonus - Vault Agent Templates

### 6.1 Template annotation

Implemented in deployment annotations:

```yaml
vault.hashicorp.com/agent-inject-template-app-config.env: |
  {{- with secret "secret/data/devops-app/config" -}}
  DATABASE_USERNAME={{ .Data.data.username }}
  DATABASE_PASSWORD={{ .Data.data.password }}
  API_KEY={{ .Data.data.api_key }}
  {{- end }}
```

This renders multiple Vault secrets into one `.env`-style file.

### 6.2 Rendered output proof

```text
/vault/secrets/app-config.env
DATABASE_USERNAME=vault-user
DATABASE_PASSWORD=vault-pass
API_KEY=vault-api-key-123
```

### 6.3 Dynamic secret refresh mechanism (research)

Vault Agent behavior:

- watches lease/token lifecycle,
- renews when possible,
- re-renders templates when source secret changes or renew events occur,
- updates injected files in shared volume.

`vault.hashicorp.com/agent-inject-command-<name>`:

- executes a command after template render/update,
- useful for reloading app config without full pod restart,
- in this lab it was used to set restrictive file permissions:

```text
vault.hashicorp.com/agent-inject-command-app-config.env: chmod 0400 /vault/secrets/app-config.env
```

### 6.4 Named template in `_helpers.tpl`

Implemented named template:

```yaml
{{- define "devops-app.envVars" -}}
- name: PORT
  value: {{ .Values.app.port | quote }}
- name: APP_ENV
  value: {{ .Values.app.environment | quote }}
- name: LOG_LEVEL
  value: {{ .Values.app.logLevel | quote }}
{{- end }}
```

Used in deployment with `include` to avoid duplication and keep env var logic DRY.

## Final Result

Lab 11 completed fully:

- Kubernetes native secrets created, inspected, decoded.
- Helm chart extended with secret template and secret injection into pods.
- Resource limits/requests configured and verified.
- Vault installed and configured (KV + Kubernetes auth + policy + role).
- Vault Agent Injector working; secrets injected as files at runtime.
- Bonus completed: template-based rendered `.env` file and named Helm templates.
