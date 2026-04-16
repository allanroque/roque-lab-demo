#!/usr/bin/env bash
# ==============================================================================
# EDA Alertmanager — Script de teste (SELinux + Disco)
# ------------------------------------------------------------------------------
# Simula webhooks do Alertmanager batendo direto no EDA, sem precisar
# alterar métricas reais no Prometheus. Útil para validar o rulebook e
# os Job Templates invocados (SNOW-INCIDENT-CREATE, SNOW-INCIDENT-CLOSE,
# SELF-HEALING-DISK-USAGE) antes da demo.
#
# Uso:
#   ./send_test_alerts.sh selinux-fire         # abre incident no SNOW
#   ./send_test_alerts.sh selinux-resolved     # fecha incident no SNOW
#   ./send_test_alerts.sh disk-fire            # roda SELF-HEALING-DISK-USAGE
#   ./send_test_alerts.sh disk-resolved        # só loga resolução
#   ./send_test_alerts.sh unrouted             # catch-all (debug no EDA)
#   ./send_test_alerts.sh all                  # roda todos em sequência
#
# Variáveis de ambiente (opcionais):
#   EDA_HOST  (default 192.168.100.11)
#   EDA_PORT  (default 5050)
#   EDA_PATH  (default /prometheus)
#   HOST_ALVO (default server01.aroque.com.br)
# ==============================================================================
set -euo pipefail

EDA_HOST="${EDA_HOST:-192.168.100.11}"
EDA_PORT="${EDA_PORT:-5050}"
EDA_PATH="${EDA_PATH:-/prometheus}"
HOST_ALVO="${HOST_ALVO:-server01.aroque.com.br}"

URL="http://${EDA_HOST}:${EDA_PORT}${EDA_PATH}"
NOW="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"

# ----- helpers --------------------------------------------------------------
log()  { printf '\033[1;36m[TEST]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[ OK ]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[FAIL]\033[0m %s\n' "$*"; exit 1; }

send() {
  local name="$1"; local payload="$2"
  log "Enviando '${name}' → ${URL}"
  local http_code
  http_code="$(curl -sS -o /tmp/_eda_resp.$$ -w '%{http_code}' \
    -H 'Content-Type: application/json' \
    -X POST "${URL}" --data-raw "${payload}" || echo '000')"
  if [[ "${http_code}" =~ ^2 ]]; then
    ok "${name} → HTTP ${http_code}"
  else
    warn "${name} → HTTP ${http_code}"
    cat /tmp/_eda_resp.$$ 2>/dev/null || true
    echo
  fi
  rm -f /tmp/_eda_resp.$$
}

# ----- payloads -------------------------------------------------------------
# SELinux firing → SNOW-INCIDENT-CREATE
payload_selinux_firing() {
cat <<EOF
{
  "version": "4",
  "status": "firing",
  "receiver": "webhook_receiver",
  "groupLabels": {"alertname": "SELinuxDisabled"},
  "commonLabels": {"alertname": "SELinuxDisabled", "severity": "security"},
  "commonAnnotations": {},
  "externalURL": "http://prometheus:9090",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "SELinuxDisabled",
        "instance": "${HOST_ALVO}",
        "severity": "security",
        "job": "linux-nodes"
      },
      "annotations": {
        "summary": "SELinux desabilitado em ${HOST_ALVO}",
        "description": "Teste sintético via send_test_alerts.sh (firing)"
      },
      "startsAt": "${NOW}",
      "endsAt": "0001-01-01T00:00:00Z",
      "generatorURL": "http://prometheus:9090/graph?g0.expr=node_selinux_config_mode",
      "fingerprint": "test-selinux-${HOST_ALVO}"
    }
  ]
}
EOF
}

# SELinux resolved → SNOW-INCIDENT-CLOSE
payload_selinux_resolved() {
cat <<EOF
{
  "version": "4",
  "status": "resolved",
  "receiver": "webhook_receiver",
  "groupLabels": {"alertname": "SELinuxDisabled"},
  "commonLabels": {"alertname": "SELinuxDisabled", "severity": "security"},
  "commonAnnotations": {},
  "externalURL": "http://prometheus:9090",
  "alerts": [
    {
      "status": "resolved",
      "labels": {
        "alertname": "SELinuxDisabled",
        "instance": "${HOST_ALVO}",
        "severity": "security",
        "job": "linux-nodes"
      },
      "annotations": {
        "summary": "SELinux re-habilitado em ${HOST_ALVO}",
        "description": "Teste sintético via send_test_alerts.sh (resolved)"
      },
      "startsAt": "${NOW}",
      "endsAt": "${NOW}",
      "generatorURL": "http://prometheus:9090/graph?g0.expr=node_selinux_config_mode",
      "fingerprint": "test-selinux-${HOST_ALVO}"
    }
  ]
}
EOF
}

# Disk firing → SELF-HEALING-DISK-USAGE
payload_disk_firing() {
cat <<EOF
{
  "version": "4",
  "status": "firing",
  "receiver": "webhook_receiver",
  "groupLabels": {"alertname": "HighFilesystemUsage"},
  "commonLabels": {"alertname": "HighFilesystemUsage", "severity": "warning"},
  "commonAnnotations": {},
  "externalURL": "http://prometheus:9090",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "HighFilesystemUsage",
        "instance": "${HOST_ALVO}",
        "severity": "warning",
        "mountpoint": "/var",
        "device": "/dev/mapper/rhel-var",
        "fstype": "xfs",
        "job": "linux-nodes"
      },
      "annotations": {
        "summary": "Filesystem /var em ${HOST_ALVO} acima de 85%",
        "description": "Teste sintético via send_test_alerts.sh — uso=88%"
      },
      "startsAt": "${NOW}",
      "endsAt": "0001-01-01T00:00:00Z",
      "generatorURL": "http://prometheus:9090/graph?g0.expr=filesystem_used",
      "fingerprint": "test-disk-${HOST_ALVO}-var"
    }
  ]
}
EOF
}

# Disk resolved → log debug
payload_disk_resolved() {
cat <<EOF
{
  "version": "4",
  "status": "resolved",
  "receiver": "webhook_receiver",
  "groupLabels": {"alertname": "HighFilesystemUsage"},
  "commonLabels": {"alertname": "HighFilesystemUsage", "severity": "warning"},
  "commonAnnotations": {},
  "externalURL": "http://prometheus:9090",
  "alerts": [
    {
      "status": "resolved",
      "labels": {
        "alertname": "HighFilesystemUsage",
        "instance": "${HOST_ALVO}",
        "severity": "warning",
        "mountpoint": "/var",
        "device": "/dev/mapper/rhel-var",
        "fstype": "xfs"
      },
      "annotations": {
        "summary": "Filesystem /var normalizado em ${HOST_ALVO}",
        "description": "Teste sintético via send_test_alerts.sh (resolved)"
      },
      "startsAt": "${NOW}",
      "endsAt": "${NOW}",
      "generatorURL": "http://prometheus:9090/graph?g0.expr=filesystem_used",
      "fingerprint": "test-disk-${HOST_ALVO}-var"
    }
  ]
}
EOF
}

# Alerta não mapeado → catch-all (debug [UNROUTED])
payload_unrouted() {
cat <<EOF
{
  "version": "4",
  "status": "firing",
  "receiver": "webhook_receiver",
  "groupLabels": {"alertname": "HighMemoryUsage"},
  "commonLabels": {"alertname": "HighMemoryUsage", "severity": "warning"},
  "commonAnnotations": {},
  "externalURL": "http://prometheus:9090",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "HighMemoryUsage",
        "instance": "${HOST_ALVO}",
        "severity": "warning"
      },
      "annotations": {
        "summary": "Memória alta em ${HOST_ALVO}",
        "description": "Teste sintético — deve cair no catch-all [UNROUTED]"
      },
      "startsAt": "${NOW}",
      "endsAt": "0001-01-01T00:00:00Z",
      "fingerprint": "test-mem-${HOST_ALVO}"
    }
  ]
}
EOF
}

# ----- dispatcher -----------------------------------------------------------
cmd="${1:-help}"
case "${cmd}" in
  selinux-fire)     send "SELinux firing"      "$(payload_selinux_firing)"  ;;
  selinux-resolved) send "SELinux resolved"    "$(payload_selinux_resolved)" ;;
  disk-fire)        send "Disk firing"         "$(payload_disk_firing)"      ;;
  disk-resolved)    send "Disk resolved"       "$(payload_disk_resolved)"    ;;
  unrouted)         send "Unrouted (memory)"   "$(payload_unrouted)"         ;;
  all)
    send "SELinux firing"      "$(payload_selinux_firing)";   sleep 3
    send "Disk firing"         "$(payload_disk_firing)";      sleep 3
    send "Unrouted (memory)"   "$(payload_unrouted)";         sleep 3
    send "SELinux resolved"    "$(payload_selinux_resolved)"; sleep 3
    send "Disk resolved"       "$(payload_disk_resolved)"
    ;;
  help|*)
    sed -n '2,22p' "$0"
    exit 0
    ;;
esac

log "Feito. Verifique:"
echo "  • EDA Activation → Jobs tab, ou: podman logs -f \$(podman ps -q --filter name=eda) 2>&1 | grep -E 'ANSIBLE|UNROUTED|Rule|Action'"
echo "  • AAP Controller → Jobs (filtrar por SNOW-INCIDENT-CREATE / SELF-HEALING-DISK-USAGE)"
echo "  • ServiceNow     → Incident list (filtrar short_description contém 'SELinux desabilitado')"
