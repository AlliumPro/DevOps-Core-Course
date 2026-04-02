{{- define "devops-app.fullname" -}}
{{- include "common.fullname" . -}}
{{- end }}

{{- define "devops-app.labels" -}}
{{- include "common.labels" . -}}
{{- end }}

{{- define "devops-app.selectorLabels" -}}
{{- include "common.selectorLabels" . -}}
{{- end }}
