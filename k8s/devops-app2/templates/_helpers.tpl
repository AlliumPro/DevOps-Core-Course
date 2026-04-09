{{- define "devops-app2.fullname" -}}
{{- include "common.fullname" . -}}
{{- end }}

{{- define "devops-app2.labels" -}}
{{- include "common.labels" . -}}
{{- end }}

{{- define "devops-app2.selectorLabels" -}}
{{- include "common.selectorLabels" . -}}
{{- end }}
