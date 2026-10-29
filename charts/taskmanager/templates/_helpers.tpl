{{/*
Коротке ім'я чарта.
*/}}
{{- define "taskmanager.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Повне ім'я об'єктів: будується з імені релізу, тому чарт можна встановити
кілька разів в один кластер. Якщо ім'я релізу вже містить ім'я чарта,
воно не дублюється.
*/}}
{{- define "taskmanager.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Назва і версія чарта для мітки helm.sh/chart.
*/}}
{{- define "taskmanager.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Мітки селектора. Виклик: include "taskmanager.selectorLabels" (dict "root" . "component" "api")
*/}}
{{- define "taskmanager.selectorLabels" -}}
app.kubernetes.io/name: {{ include "taskmanager.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/*
Повний набір міток. Виклик: include "taskmanager.labels" (dict "root" . "component" "api")
*/}}
{{- define "taskmanager.labels" -}}
helm.sh/chart: {{ include "taskmanager.chart" .root }}
{{ include "taskmanager.selectorLabels" . }}
app.kubernetes.io/version: {{ .root.Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
{{- end }}
