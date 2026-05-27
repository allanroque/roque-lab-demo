# Roteiro de testes — Chaos Engineering AIOps

Validar que **falha de componente → alerta Prometheus → EDA → pipeline AIOps**.

## Job Templates criados (org ROQUE)

| ID  | Nome | Playbook | Survey | Creds |
|-----|------|----------|--------|-------|
| 417 | AIOPS-CHAOS-INJECT | `playbooks/aiops/chaos/inject_alert_failure.yml` | ✅ | `ask_credential_on_launch` (use **CRED-SSH-LINUX-ROQUE**) |
| 418 | AIOPS-CHAOS-VERIFY | `playbooks/aiops/chaos/verify_alert_firing.yml` | ✅ | nenhuma (uri local) |
| 419 | AIOPS-CHAOS-SETUP-SURVEYS | `playbooks/aiops/chaos/setup_chaos_jt_surveys.yml` | — | **CRED-AAP-ROQUE** (idempotente, já rodado uma vez) |

## Famílias de alerta suportadas (`alert_family`)

| Família | Componente quebrado | Restore |
|---------|---------------------|---------|
| `apache`    | `systemctl stop httpd` | `start + enable + unmask` |
| `app`       | `systemctl stop {{ app_service_name }}` (default httpd) | start + enable |
| `chrony`    | `systemctl stop chronyd` | start + enable |
| `firewall`  | `systemctl stop firewalld` | start + enable |
| `postgres`  | `systemctl stop {{ postgres_service_name }}` (default postgresql) | start + enable |
| `rsyslog`   | `systemctl stop rsyslog` | start + enable |
| `selinux`   | `setenforce 0` (Permissive) — salva estado prévio em `/var/lib/aiops-chaos/selinux.before` | `setenforce 1` |
| `all`       | todas as anteriores em sequência | — |

## Fluxo de teste — UM componente

```text
1) AIOPS-CHAOS-INJECT  (Survey)
   - alert_family: apache
   - mode: break
   - chaos_targets: server01.aroque.com.br
   - SSH cred: CRED-SSH-LINUX-ROQUE

2) AIOPS-CHAOS-VERIFY  (Survey)
   - alert_family: apache
   - prometheus_url: http://localhost:9090
   - max_retries: 12 (60s)
   → confirma alertname=ApacheDown / AppDown / HTTPDown em firing

3) (Automático via EDA)  WF-AIOPS-ENRICHMENT  -> cria INC + popula survey do WF-2
4) WF-AIOPS-REMEDIATION (id 414)
   → gera playbook IA → commit → executa → enriquece EDA → fecha SNOW

5) AIOPS-CHAOS-VERIFY de novo
   → confirma alerta resolvido
```

## Fluxo de stress — TODAS as famílias

Lançar `AIOPS-CHAOS-INJECT` com `alert_family: all` e `mode: break` para quebrar
tudo de uma vez. Observa o Prometheus em http://localhost:9090/alerts e o EDA
em http://aap01.aroque.com.br para ver os pipelines AIOps em paralelo.

Para **restaurar tudo**: `alert_family: all`, `mode: restore`.

## Exemplos de extra_vars (sem usar survey)

**Quebrar Apache em server01**
```yaml
alert_family: apache
mode: break
chaos_targets: server01.aroque.com.br
```

**Restaurar PostgreSQL**
```yaml
alert_family: postgres
mode: restore
chaos_targets: db01.aroque.com.br
postgres_service_name: postgresql-15
```

**Verificar disparo de alerta chrony**
```yaml
alert_family: chrony
prometheus_url: http://localhost:9090
max_retries: 24
retry_delay: 5
```

## stats exportadas

- **INJECT** → `stats_chaos_family`, `stats_chaos_mode`, `stats_chaos_targets`, `stats_chaos_post_status`
- **VERIFY** → `stats_alert_fired`, `stats_alert_matched_names`, `stats_alert_query_url`

## Notas

- O playbook é idempotente — rodar `mode: restore` várias vezes não causa problema.
- SELinux: o estado anterior fica em `/var/lib/aiops-chaos/selinux.before` no host.
- Postgres: `failed_when: false` no break/restore para tolerar host sem postgres instalado.
- O `wait_seconds_after_break` (default 30s) dá tempo do Prometheus avaliar antes do INJECT terminar.
