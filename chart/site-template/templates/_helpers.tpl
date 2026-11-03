{{- define "site.authSecret" -}}
{{- $existing := lookup "v1" "Secret" .Release.Namespace (printf "%s-app" .Release.Name) -}}
{{- if and $existing $existing.data (index $existing.data "AUTH_SECRET") -}}
{{- index $existing.data "AUTH_SECRET" | b64dec -}}
{{- else -}}
{{- randAlphaNum 64 -}}
{{- end -}}
{{- end -}}

{{- define "site.minioPassword" -}}
{{- $existing := lookup "v1" "Secret" .Release.Namespace (printf "%s-app" .Release.Name) -}}
{{- if and $existing $existing.data (index $existing.data "MINIO_SECRET_KEY") -}}
{{- index $existing.data "MINIO_SECRET_KEY" | b64dec -}}
{{- else -}}
{{- randAlphaNum 32 -}}
{{- end -}}
{{- end -}}

{{- define "site.betterAuthURL" -}}
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

{{- define "site.appName" -}}
{{- default .Chart.Name .Values.appName | default "SITE_NAME" -}}
{{- end -}}
