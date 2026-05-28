# Guia de Demo — AIOps Self-Healing com Ansible Automation Platform

> **Duração**: 25–35 min
> **Público**: arquitetos, gerentes de infra, SREs, decisores técnicos
> **Stack**: AAP 2.6 + EDA + Prometheus/Alertmanager + ServiceNow + LiteLLM (deepseek-r1)
> **Cenário lab**: ORG ROQUE, hosts server01/server02/server03

---

## 🎬 A história em 3 atos

> **Ato 1 — A dor real**
> "São 3 da manhã. Um alerta dispara: `ApacheDown` em server01. O on-call é acordado, abre o runbook, conecta no host, descobre que o systemd masked o serviço, executa o fix, fecha o incidente. 40 minutos depois, volta pra dormir.
>
> Pergunta: e se essa mesma falha acontecer amanhã em outro host? E se for um serviço diferente, sem runbook? E se a equipe não conhecer a causa raiz?"
>
> **Ato 2 — Automation as code, mas pra coisa NOVA**
> "AAP automatiza o que você já sabe. Mas a vida real tem alertas SEM runbook. A gente trouxe IA pra esse buraco: ela investiga, escreve o playbook, commita, executa — tudo isso enriquecendo o ServiceNow. O humano só revisa o prompt e aprova."
>
> **Ato 3 — Self-healing real**
> "Uma vez que a IA gera um playbook que funciona, a plataforma APRENDE: na próxima vez que o mesmo alerta firar, o EDA já dispara o playbook direto, sem passar pela IA. 40 minutos viraram 8 segundos."

---

## 📐 Arquitetura em 1 slide

```
┌─────────────────┐    fire    ┌──────────────────┐         ┌─────────────────────┐
│ Prometheus +    │ ─────────▶ │  EDA Rulebook    │ ──────▶ │  AAP Workflow / JT  │
│ Alertmanager    │            │  (alertname → ?) │         │  (Ansible Playbook) │
└─────────────────┘            └─────┬────────────┘         └──────────┬──────────┘
                                     │ unknown                          │ executa
                                     ▼                                   ▼
                          ┌─────────────────────┐               ┌──────────────┐
                          │ WF-AIOPS-ENRICH (IA)│               │   Server     │
                          │  RCA → SNOW INC     │               │   (fixed)    │
                          └──────────┬──────────┘               └──────────────┘
                                     │ humano revisa prompt
                                     ▼
                          ┌──────────────────────────┐
                          │ WF-AIOPS-REMEDIATION (IA)│
                          │  gera playbook → commit  │
                          │  executa → auto-learn    │
                          │  EDA rule → fecha SNOW   │
                          └──────────────────────────┘
```

**Mensagem-chave**: o EDA é o cérebro reativo. Ele tenta primeiro a automação conhecida; se não tem, escala pra IA. Cada loop pelo caminho IA gera uma nova regra automática.

---

## 🎯 Sequência de demo (live, ~30 min)

### Etapa 0 — Setup do palco (1 min, antes de começar)

Abra 4 abas no browser:

| Aba | URL | Para mostrar |
|-----|-----|--------------|
| 1 | `https://aap01.aroque.com.br/jobs` | AAP — fila de jobs |
| 2 | `https://aap01.aroque.com.br/ui_eda/activations` | EDA — Activations |
| 3 | `http://192.168.100.1:9090/alerts` | Prometheus — alertas |
| 4 | (ServiceNow) | Incidentes |

> 🗣️ **Fala**: "Esse é o ambiente real de um lab. Tem AAP, EDA, Prometheus monitorando hosts Linux, e SNOW pra ticketing. Antes da demo, eu já automatizei `SELinuxDisabled` e `AppDown` na ORG ROQUE — são meus casos de uso conhecidos."

---

### Etapa 1 — Mostrar o EDA escutando (2 min)

**Mostre na aba EDA**:
- Activation `ALERTMANAGER-EVENTS-ROQUE` em `running`
- `rules_count: 25`, `rules_fired_count: > 50`

**Mostre o rulebook** (`rulebooks/alert/alertmanager_events.yml`):

```yaml
- name: "AIOps Fallback — AppDown (sem automação prévia)"
  condition: event.alert.labels.alertname == "AppDown" and event.alert.status == "firing"
  action:
    run_workflow_template:
      name: "WF-AIOPS-ENRICHMENT"
```

> 🗣️ **Fala**: "Olha o que essa regra diz: 'se o alerta `AppDown` firar, dispara o pipeline AIOps'. Não tem playbook hardcoded. A IA vai decidir o que fazer."

---

### Etapa 2 — Provocar a falha (chaos engineering) (3 min)

**No AAP → Templates → AIOPS-CHAOS-INJECT** (id 417). Mostre o **Survey**:
- alert_family: `apache`
- mode: `break`
- chaos_targets: `server01.aroque.com.br`

> 🗣️ **Fala**: "Pra demonstrar, eu mesmo vou quebrar o ambiente. Em produção, é a falha real que dispara. Aqui é controlado."

**Launch** → mostre o job rodando — vai parar o httpd em server01.

**Aba Prometheus**: refresh → alerta **`AppDown`** vai aparecer em `pending` → `firing` em ~30s.

> 🗣️ **Fala**: "O Prometheus detectou em 30 segundos. Em produção: PagerDuty, Slack, on-call acordado. Aqui: o EDA já está escutando."

---

### Etapa 3 — O EDA aciona o pipeline AIOps (4 min)

**Aba AAP Jobs**: refresh → vai aparecer um workflow `WF-AIOPS-ENRICHMENT` rodando, **launched_by = roque (EDA)**.

Clica no workflow e mostra os 5 nodes em execução em tempo real:

```
1. AIOPS-COLLECT-HOST-CONTEXT  →  pega journalctl, systemctl status, dmesg
2. AIOPS-CHECK-SERVICE-STATUS  →  estado do serviço
3. AIOPS-ANALYZE-INCIDENT      →  IA gera RCA (deepseek-r1, ~10s)
4. AIOPS-CREATE-SNOW-INC       →  abre INC no ServiceNow com RCA
5. AIOPS-BUILD-REMEDIATION-JT  →  popula o survey do WF-2 com sugestão
```

**Aba SNOW**: refresh → vai aparecer um novo INC com:
- Description: "Chronyd parado em server03..."
- **Work Notes**: RCA da IA explicando que httpd foi mascarado pelo systemd
- Field `ai_prompt_suggestion`: prompt sugerido pra remediar

> 🗣️ **Fala**: "Em 90 segundos, sem intervenção humana, eu tenho: incidente aberto no ServiceNow, causa raiz analisada pela IA, e um prompt sugerido pra gerar o playbook. O humano agora entra como CURADOR — não mais como executor."

---

### Etapa 4 — O humano revisa e libera (3 min)

**Volta no AAP → Templates → WF-AIOPS-REMEDIATION**. Mostra o **Survey já populado** automaticamente pelo nó BUILD-REMEDIATION-JT:

- sn_incident_number: `INC0017650`
- target_host: `server01.aroque.com.br`
- service_name: `httpd`
- **prompt_manual**: "Crie um playbook idempotente que..." (sugestão da IA)

> 🗣️ **Fala**: "Em ambiente real, esse prompt cai num canal do Slack via ChatOps, o on-call lê, ajusta se quiser, clica em '✅ Aprovar'. Hoje quem aprova é o humano. Amanhã pode virar policy."

**Edite ligeiramente o prompt pra mostrar que dá controle** → **Launch**.

---

### Etapa 5 — A mágica do AIOps (5 min)

Mostre o workflow rodando os 5 nodes:

```
1. AIOPS-GENERATE-PLAYBOOK    →  IA gera YAML do playbook (deepseek-r1, ~20s)
                                  - usa <think> tags, code fences, FQCN
                                  - validação automática: hosts/tasks/sem shell

2. AIOPS-COMMIT-TO-GIT         →  commit em playbooks/ai-generated/<timestamp>.yml
                                  - push direto na main com token autenticado

3. AIOPS-BUILD-EXECUTE-JT      →  project sync + PATCH JT dinâmico
                                  AIOPS-DYN-INC0017650 + executa em server01

4. AIOPS-ENRICH-EDA            →  adiciona NOVA regra no rulebook:
                                  "se AppDown firar de novo, vá DIRETO no JT"
                                  + sync EDA + restart Activation

5. SNOW-INCIDENT-CLOSE         →  fecha INC0017650 com nota de fechamento
```

**Aba AAP**: workflow vira tudo verde. ~115s total.

**Aba GitHub** (opcional): mostre o commit `feat(aiops): playbook gerado pela IA para INC0017650` com o arquivo novo em `playbooks/ai-generated/`.

> 🗣️ **Fala**: "Olha o que aconteceu nos últimos 2 minutos:
> 1. A IA escreveu um playbook Ansible idempotente
> 2. Commitou no git (auditoria pronta — quem fez? a IA, no INC tal)
> 3. Executou no host e remediou
> 4. Aprendeu: gerou uma regra no EDA pra próxima vez NÃO chamar mais a IA
> 5. Fechou o incidente no ServiceNow.
>
> Quanto custou? Zero clique humano depois da aprovação."

---

### Etapa 6 — O sistema APRENDEU (3 min)

**Mostre o rulebook atualizado**:

```yaml
# BEGIN AIOPS AUTO-LEARN: AppDown
- name: "AUTO-LEARN — AppDown → AIOPS-DYN-INC0017650"
  condition: event.alert.labels.alertname == "AppDown" and event.alert.status == "firing"
  action:
    run_job_template:
      name: "AIOPS-DYN-INC0017650"
```

> 🗣️ **Fala**: "Essa regra NÃO existia antes da demo. A IA a criou. Agora se eu quebrar Apache de novo, o EDA vai DIRETO no JT — sem IA, sem ticket, em segundos."

**Faça a demo de loop fechado**:
- Quebra Apache de novo (CHAOS-INJECT apache=break)
- Mostre o EDA disparando `AIOPS-DYN-INC0017650` direto (sem WF-AIOPS-ENRICHMENT)
- Apache volta em **~8 segundos**

> 🗣️ **Fala**: "Esse é o ciclo do AIOps. A primeira vez, IA + humano + 2 minutos. A segunda vez, máquina pura, 8 segundos. Quanto mais o ambiente é exercitado, mais ele se cura sozinho."

---

### Etapa 7 — Auto-remediação para alertas conhecidos (3 min)

**Mostre os JTs já cadastrados**:

| JT | Serviço | Trigger EDA |
|----|---------|-------------|
| REMEDIATION-RSYSLOG (id 421) | rsyslog | RsyslogDown firing |
| REMEDIATION-CHRONY (id 422) | chronyd | ChronyDown firing |
| REMEDIATION-FIREWALL (id 423) | firewalld | FirewalldDown firing |
| REMEDIATION-SELINUX (id 324) | selinux | SELinuxDisabled firing |

**Demo loop curto**:
- CHAOS-INJECT chrony=break server03
- ~90s depois mostre `REMEDIATION-CHRONY` rodando com `extra_vars.ansible_eda` (prova que foi o EDA)
- chronyd volta a active

> 🗣️ **Fala**: "Pra alertas conhecidos a remediação é instantânea. Pra alertas novos, a IA entra. É a mesma plataforma, dois modos de operação."

---

### Etapa 8 — Encerramento (2 min)

**Slide ou fala**:

> "O que vocês acabaram de ver não é teoria — é um ambiente real que vai pra produção. O diferencial: **a IA é guard-railed**. Ela:
> - Só atua com aprovação humana na primeira vez
> - Versiona TUDO em git (auditoria completa)
> - Enriquece o ServiceNow (compliance e ITSM)
> - Aprende e elimina seu próprio uso (cost-aware)
>
> O ROI: cada incidente que o humano resolve UMA vez vira automação eterna. E a IA cobre o gap dos alertas novos sem precisar contratar mais SREs."

**Métricas para citar** (do lab):
- ⏱️ MTTR antes: ~40min (humano com runbook)
- ⏱️ MTTR primeira vez (IA): ~2min
- ⏱️ MTTR após auto-learn: **~8s**
- 📝 Auditoria: 100% no git + SNOW
- 🤖 Modelo: deepseek-r1 (self-hosted via LiteLLM, custo previsível)

---

## 🛡️ Perguntas frequentes & respostas

| Pergunta | Resposta |
|----------|----------|
| "E se a IA gerar playbook errado?" | Validação automática (FQCN, sem shell/raw, sintaxe YAML). E o humano aprova o prompt antes de executar. Em produção: dry-run obrigatório com `--check --diff` antes do live. |
| "Custo do LLM?" | LiteLLM self-hosted com modelos abertos (deepseek-r1, llama). Custo previsível por inferência. Cada incidente = ~10-20 tokens out. |
| "E compliance?" | Tudo em git (auditoria), tudo em SNOW (ITSM), tudo com signed commits possíveis. RBAC do AAP controla quem aprova. |
| "Funciona em ambiente air-gapped?" | Sim. Modelos open-source rodam no AAP node (ou cluster GPU separado). Não depende de OpenAI/Anthropic externos. |
| "E quando o playbook gerado fica obsoleto?" | A auto-learn rule pode ser regenerada. Em produção, recomenda-se TTL nas regras geradas e re-validação periódica. |
| "Quem tem responsabilidade legal pelo playbook da IA?" | Igual a um humano: passou na aprovação, foi commitado por bot autorizado, está em git. A trilha é mais clara que processo manual. |

---

## 🧪 Cheat sheet de comandos para a demo

### Forçar chaos durante a demo
```yaml
# AIOPS-CHAOS-INJECT (JT id 417, survey)
alert_family: apache       # ou app, chrony, firewall, rsyslog, postgres, selinux
mode: break                # ou restore
chaos_targets: server01.aroque.com.br
```

### Lançar WF-AIOPS-REMEDIATION (manual review)
```yaml
sn_incident_number: INC0017650
target_host: server01.aroque.com.br
service_name: httpd
alertname: AppDown
prompt_manual: "Crie playbook idempotente..."
```

### Probe Prometheus
```
http://192.168.100.1:9090/alerts
http://192.168.100.1:9090/api/v1/alerts  (JSON)
```

### Resetar ambiente ao fim da demo
```yaml
# AIOPS-CHAOS-INJECT
alert_family: all
mode: restore
chaos_targets: lab_servers   # grupo do inventário
```

---

## ⏱️ Roteiro de tempo (resumo)

| Etapa | Tempo | Mensagem |
|-------|-------|----------|
| 0. Setup palco | 1m | Aqui é real, não vídeo |
| 1. EDA escutando | 2m | Cérebro reativo |
| 2. Provocar falha | 3m | Chaos engineering controlado |
| 3. EDA aciona AIOps | 4m | Sem clique humano |
| 4. Humano revisa | 3m | Aprovação, não execução |
| 5. IA executa | 5m | Gera + commita + executa + fecha |
| 6. Auto-learn | 3m | Loop fechado, 40min→8s |
| 7. Auto-remediação known | 3m | Conhecido = instantâneo |
| 8. Encerramento + QA | 5–10m | ROI e perguntas |

**Total: 25–35 min** (depende do ambiente — IA pode levar 10–30s extras).

---

## 🎁 Bônus — Demo "do zero" (15 min, para audiência técnica)

Se a audiência for técnica e quiser ver o **playbook IA-gerado**, abra:
- `playbooks/ai-generated/<timestamp>_INC0017650.yml` no GitHub
- Mostre a estrutura: `- name:`, `hosts:`, `tasks:` com FQCN, `set_stats` final

E o **system prompt** que orienta a IA:
- `playbooks/aiops/templates/playbook_system_prompt.j2`

Mostre as **regras rigorosas**: FQCN obrigatório, sem shell/raw, `<think>` tags pra reasoning, code fence pra YAML.

> 🗣️ **Fala**: "O segredo não é a IA. É o **system prompt + validação**. Sem isso, a IA gera lixo. Com isso, ela vira um SRE júnior produtivo."
