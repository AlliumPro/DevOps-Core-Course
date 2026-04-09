{{- define "devops-app.fullname" -}}
{{- include "common.fullname" . -}}
{{- end }}

{{- define "devops-app.labels" -}}
{{- include "common.labels" . -}}
{{- end }}

{{- define "devops-app.selectorLabels" -}}
{{- include "common.selectorLabels" . -}}
{{- end }}

{{- define "devops-app.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (printf "%s-sa" (include "devops-app.fullname" .)) .Values.serviceAccount.name -}}
{{- else }}
{{- default "default" .Values.serviceAccount.name -}}
{{- end }}
{{- end }}

{{- define "devops-app.secretName" -}}
{{- if .Values.secret.name }}
{{- .Values.secret.name -}}
{{- else }}
{{- printf "%s-secret" (include "devops-app.fullname" .) -}}
{{- end }}
{{- end }}

{{- define "devops-app.envVars" -}}
- name: PORT
  value: {{ .Values.app.port | quote }}
- name: APP_ENV
  value: {{ .Values.app.environment | quote }}
- name: LOG_LEVEL
  value: {{ .Values.app.logLevel | quote }}
{{- end }}
