{{/*
AUTH_SECRET: reuse existing Secret across upgrades; mint once on first install.
*/}}
{{- define "olaresdemo.authSecret" -}}
{{- $existing := lookup "v1" "Secret" .Release.Namespace (printf "%s-app" .Release.Name) -}}
{{- if and $existing $existing.data (index $existing.data "AUTH_SECRET") -}}
{{- index $existing.data "AUTH_SECRET" | b64dec -}}
{{- else -}}
{{- randAlphaNum 64 -}}
{{- end -}}
{{- end -}}

{{/*
MINIO_ROOT_PASSWORD: same generate-once pattern.
*/}}
{{- define "olaresdemo.minioPassword" -}}
{{- $existing := lookup "v1" "Secret" .Release.Namespace (printf "%s-app" .Release.Name) -}}
{{- if and $existing $existing.data (index $existing.data "MINIO_SECRET_KEY") -}}
{{- index $existing.data "MINIO_SECRET_KEY" | b64dec -}}
{{- else -}}
{{- randAlphaNum 32 -}}
{{- end -}}
{{- end -}}

{{/*
Public base URL for Better Auth. Prefer Settings override, else entrance host.
*/}}
{{- define "olaresdemo.betterAuthURL" -}}
{{- $oe := .Values.olaresEnv | default dict -}}
{{- $override := index $oe "BETTER_AUTH_URL" | default "" -}}
{{- if $override -}}
{{- $override | trimSuffix "/" -}}
{{- else -}}
{{- $raw := index (.Values.domain | default dict) "web" | default "" -}}
{{- $host := (splitList "," $raw | first) | default "" -}}
{{- if $host -}}
{{- printf "https://%s" $host -}}
{{- else -}}
{{- "http://localhost:3000" -}}
{{- end -}}
{{- end -}}
{{- end -}}
