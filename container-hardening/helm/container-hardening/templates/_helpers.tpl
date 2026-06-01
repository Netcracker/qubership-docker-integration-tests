{{/*
Expand the name of the chart.
*/}}
{{- define "container-hardening.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "container-hardening.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "container-hardening.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Pod-level security context.
Enforces runAsNonRoot and seccompProfile; merges in any additional context from global.securityContext.
*/}}
{{- define "container-hardening.globalPodSecurityContext" -}}
runAsNonRoot: true
seccompProfile:
  type: "RuntimeDefault"
{{- if eq .Values.PAAS_PLATFORM "KUBERNETES" }}
runAsUser: 1000
runAsGroup: 1000
{{- end }}
{{- with .Values.global.securityContext }}
{{ toYaml . }}
{{- end -}}
{{- end -}}

{{/*
Container-level security context.
*/}}
{{- define "container-hardening.globalContainerSecurityContext" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: ["ALL"]
{{- end -}}

{{/*
Common labels applied to all resources.
*/}}
{{- define "container-hardening.labels" -}}
helm.sh/chart: {{ include "container-hardening.chart" . }}
{{ include "container-hardening.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: '{{ .Values.ARTIFACT_DESCRIPTOR_VERSION | trunc 63 | trimAll "-_." }}'
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: '{{ .Values.PART_OF | trunc 63 | trimSuffix "-" }}'
{{- with .Values.ARTIFACT_DESCRIPTOR_VERSION }}
app.kubernetes.io/component-version: {{ . | trunc 63 | trimAll "-_." | toString | quote }}
{{- end }}
{{- end -}}

{{/*
Selector labels.
*/}}
{{- define "container-hardening.selectorLabels" -}}
app.kubernetes.io/name: {{ include "container-hardening.name" . }}
app.kubernetes.io/instance: {{ .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end -}}

{{/*
Resolve the container-hardening runner image.
When the App Deployer injects .Values.deployDescriptor the image is read from
the descriptor; otherwise falls back to .Values.containerHardening.image so
the chart keeps working standalone.
*/}}
{{- define "find_image" -}}
  {{- $image := .default -}}
  {{- if .vals.deployDescriptor -}}
    {{- if index .vals.deployDescriptor .deployName -}}
      {{- $image = (index .vals.deployDescriptor .deployName "image") -}}
    {{- else if index .vals.deployDescriptor .SERVICE_NAME -}}
      {{- $image = (index .vals.deployDescriptor .SERVICE_NAME "image") -}}
    {{- end -}}
  {{- end -}}
  {{- printf "%s" $image -}}
{{- end -}}

{{- define "container-hardening.findImage" -}}
  {{- include "find_image" (dict "deployName" "containerHardening" "SERVICE_NAME" "container-hardening-image" "vals" .Values "default" .Values.containerHardening.image) -}}
{{- end -}}
