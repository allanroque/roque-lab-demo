#!/usr/bin/env python3
"""
Aplica surveys nos Job Templates ROQUE alinhados ao padrão SRE (DNS, IPAM, SNOW, ADHOC).
Requer AAP_ADMIN_TOKEN ou token admin no .mcp.json (linha Bearer b4td…).
"""
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

BASE = "https://aap01.aroque.com.br/api/controller/v2"
ORG_ROQUE_PROJECT = "PROJ-GIT-ROQUE-LAB"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def get_token():
    t = os.environ.get("AAP_ADMIN_TOKEN", "").strip()
    if t:
        return t
    p = os.path.join(os.path.dirname(__file__), ".mcp.json")
    with open(p, encoding="utf-8") as f:
        for line in f:
            if "b4td" in line and "Bearer" in line:
                return line.split("Bearer")[-1].strip().strip('",')
    raise SystemExit("AAP_ADMIN_TOKEN ou .mcp.json com Bearer admin")


TOKEN = get_token()


def api(method, path, data=None):
    url = BASE + path
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=120) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"HTTP {e.code} {method} {path}\n{err}", file=sys.stderr)
        raise


# Pergunta padrão (formato compatível com controller / SRE)
def q_text(var, qname, desc="", default="", required=False, max_len=1024):
    return {
        "max": max_len,
        "min": 0,
        "type": "text",
        "choices": [],
        "default": default,
        "required": required,
        "variable": var,
        "new_question": True,
        "question_name": qname,
        "question_description": desc,
    }


def q_multi(var, qname, choices, desc="", default="", required=False):
    return {
        "max": 1024,
        "min": 0,
        "type": "multiplechoice",
        "choices": choices,
        "default": default,
        "required": required,
        "variable": var,
        "new_question": True,
        "question_name": qname,
        "question_description": desc,
    }


def q_integer(var, qname, desc="", default=0, required=False, min_v=0, max_v=999999):
    return {
        "min": min_v,
        "max": max_v,
        "type": "integer",
        "choices": [],
        "default": default,
        "required": required,
        "variable": var,
        "new_question": True,
        "question_name": qname,
        "question_description": desc,
    }


# (jt_name, survey_body) — body = {"name":"","description":"","spec":[...]}
SURVEYS = [
    (
        "DNS-ADD-RECORD",
        {
            "name": "",
            "description": "Alinhado ao SRE DNS-ADD-RECORD; variáveis do playbook add_record.yml",
            "spec": [
                q_text(
                    "host_name",
                    "Hostname Completo (FQDN)",
                    "Ex: web01.aroque.com.br",
                    "web01.aroque.com.br",
                    False,
                    40,
                ),
                q_text(
                    "host_ip",
                    "Endereço IP do Host",
                    "Ex: 192.168.100.50",
                    "192.168.100.50",
                    False,
                    40,
                ),
            ],
        },
    ),
    (
        "DNS-DEL-RECORD",
        {
            "name": "",
            "description": "Alinhado ao SRE DNS-DEL-RECORD",
            "spec": [
                q_text(
                    "host_name",
                    "Hostname Completo (FQDN)",
                    "Ex: web01.aroque.com.br",
                    "web01.aroque.com.br",
                    False,
                    40,
                ),
            ],
        },
    ),
    (
        "DNS-RESOLV-RECORD",
        {
            "name": "",
            "description": "resolv_record.yml — teste de resolução",
            "spec": [
                q_text(
                    "host_name",
                    "FQDN a resolver",
                    "Ex: server01.aroque.com.br",
                    "",
                    False,
                    1024,
                ),
                q_text(
                    "dns_server",
                    "Servidor DNS para consulta",
                    "Default no playbook: 192.168.100.11",
                    "192.168.100.11",
                    False,
                    40,
                ),
            ],
        },
    ),
    (
        "IPAM-ADD-IP",
        {
            "name": "",
            "description": "add_ip.yml — host_name curto, IP e descrição",
            "spec": [
                q_text("host_name", "Nome curto do host", "Ex: server01", "", False, 1024),
                q_text("host_ip", "IP a registrar", "Ex: 192.168.100.60", "", False, 1024),
                q_text(
                    "host_description",
                    "Descrição do registro",
                    "",
                    "Configured by Ansible",
                    False,
                    1024,
                ),
            ],
        },
    ),
    (
        "IPAM-DEL-IP",
        {
            "name": "",
            "description": "del_ip.yml",
            "spec": [
                q_text(
                    "host_ip",
                    "Remover IP do NetBox",
                    "Ex: 192.168.100.51",
                    "",
                    False,
                    40,
                ),
            ],
        },
    ),
    (
        "IPAM-GET-NEXT-IP",
        {
            "name": "",
            "description": "get_next_ip.yml — netbox_url/token via credencial/controller",
            "spec": [
                q_text("host_name", "Nome curto do host", "Ex: web01", "", False, 1024),
                q_text(
                    "host_description",
                    "Descrição",
                    "",
                    "Configured by Ansible",
                    False,
                    1024,
                ),
                q_text(
                    "net_prefix",
                    "Rede (prefix)",
                    "",
                    "192.168.100.0",
                    False,
                    64,
                ),
                q_text("net_cidr", "CIDR", "", "24", False, 8),
            ],
        },
    ),
    (
        "SNOW-INCIDENT-CREATE",
        {
            "name": "",
            "description": "Espelha SRE SNOW-INCIDENT-CREATE (incident_create.yml)",
            "spec": [
                q_text(
                    "sn_short_description",
                    "Resumo curto do incidente",
                    "",
                    "",
                    False,
                ),
                q_text(
                    "sn_description",
                    "Descrição detalhada",
                    "",
                    "",
                    False,
                ),
                q_multi(
                    "sn_impact",
                    "Impact",
                    ["high", "medium", "low"],
                    "Nível de impacto",
                ),
                q_multi(
                    "sn_urgency",
                    "Urgency",
                    ["high", "medium", "low"],
                    "",
                ),
            ],
        },
    ),
    (
        "SNOW-INCIDENT-CLOSE",
        {
            "name": "",
            "description": "Espelha SRE SNOW-INCIDENT-CLOSE",
            "spec": [
                q_text(
                    "sn_incident_number",
                    "Número do incidente a fechar",
                    "Ex: INC0010001",
                    "",
                    False,
                ),
                q_multi(
                    "sn_close_code",
                    "Close code",
                    [
                        "Solved (Permanently)",
                        "Solved (Work Around)",
                        "Solved Remotely (Work Around)",
                        "Solved Remotely (Permanently)",
                    ],
                    "",
                ),
                q_text(
                    "sn_close_notes",
                    "Notas de fechamento",
                    "",
                    "",
                    False,
                ),
            ],
        },
    ),
    (
        "SNOW-CHANGE-CREATE",
        {
            "name": "",
            "description": "change_create.yml — usa sn_impact_value, sn_urgency_value, sn_category_value",
            "spec": [
                q_text("sn_short_description", "Short description", "", "Change via Ansible", False),
                q_text("sn_description", "Description", "", "", False),
                q_multi(
                    "sn_impact_value",
                    "Impact",
                    ["high", "medium", "low"],
                    "",
                ),
                q_multi(
                    "sn_urgency_value",
                    "Urgency",
                    ["high", "medium", "low"],
                    "",
                ),
                q_multi(
                    "sn_category_value",
                    "Category",
                    [
                        "network",
                        "hardware",
                        "software",
                        "application",
                        "security",
                        "infrastructure",
                        "other",
                    ],
                    "",
                ),
            ],
        },
    ),
    (
        "SNOW-CHANGE-CLOSE",
        {
            "name": "",
            "description": "change_close.yml — sn_change_request_number, sn_closure_code, sn_closure_notes",
            "spec": [
                q_text(
                    "sn_change_request_number",
                    "Número da change",
                    "Ex: CHG0010001",
                    "",
                    False,
                ),
                q_multi(
                    "sn_closure_code",
                    "Código de fechamento",
                    [
                        "successful",
                        "successful_with_issues",
                        "unsuccessful",
                        "cancelled",
                        "backed_out",
                    ],
                    "Ajuste aos valores do dicionário ServiceNow, se necessário",
                ),
                q_text(
                    "sn_closure_notes",
                    "Notas de fechamento",
                    "",
                    "Change successfully implemented",
                    False,
                ),
            ],
        },
    ),
    (
        "LINUX-ADHOC-COMMAND",
        {
            "name": "",
            "description": "Como SRE LINUX-ADHOC-COMMAND — my_command",
            "spec": [
                q_multi(
                    "my_command",
                    "Comando (seguro para lab)",
                    [
                        "echo Test Ansible Command!",
                        "hostname",
                        "uptime",
                        "df -h",
                        "free -h",
                        "ss -tuln",
                    ],
                    "Playbook usa ansible.builtin.command",
                ),
            ],
        },
    ),
    (
        "LINUX-CONFIG-DNS",
        {
            "name": "",
            "description": "Como SRE LINUX-CONFIG-DNS — dns_servers",
            "spec": [
                q_multi(
                    "dns_servers",
                    "Servidor(es) DNS",
                    [
                        "8.8.8.8",
                        "192.168.100.11",
                        "1.1.1.1",
                        "10.216.165.10",
                    ],
                    "Valor único; playbook normaliza para lista",
                ),
                q_text(
                    "target_interface",
                    "Interface (opcional)",
                    "Vazio = interface primária",
                    "",
                    False,
                    64,
                ),
            ],
        },
    ),
    (
        "PROVISION-VM-LOCAL",
        {
            "name": "",
            "description": "provision_vm.yml — VMware Fusion local (vmrest); credenciais vmrest no JT",
            "spec": [
                q_text(
                    "host_name",
                    "Nome do host (curto)",
                    "Ex: server03 (sem FQDN)",
                    "",
                    True,
                    128,
                ),
                q_text(
                    "host_ip",
                    "IP do host",
                    "Ex: 192.168.100.50",
                    "",
                    True,
                    40,
                ),
                q_text(
                    "host_domain",
                    "Domínio DNS",
                    "Sufixo FQDN",
                    "aroque.com.br",
                    False,
                    128,
                ),
                q_text(
                    "host_description",
                    "Descrição",
                    "Inventário / CMDB",
                    "Provisioned by Ansible",
                    False,
                    512,
                ),
                q_integer(
                    "host_cpus",
                    "vCPUs",
                    "Configura a VM (vmrest) e exporta valor confirmado pela API (CMDB)",
                    2,
                    False,
                    1,
                    64,
                ),
                q_integer(
                    "host_memory_mb",
                    "RAM (MB)",
                    "Configura a VM (vmrest) e exporta valor confirmado pela API (CMDB)",
                    2048,
                    False,
                    512,
                    262144,
                ),
                q_text(
                    "host_disk",
                    "Disco (informativo)",
                    "CMDB — vmrest não altera disco; ex: 40GB",
                    "",
                    False,
                    64,
                ),
                q_multi(
                    "host_role",
                    "Função (role)",
                    ["webserver", "database", "app", "bastion"],
                    "Papel do servidor",
                    "webserver",
                    False,
                ),
                q_multi(
                    "host_group",
                    "Grupo",
                    ["lab", "prod", "staging"],
                    "Grupo lógico",
                    "lab",
                    False,
                ),
                q_multi(
                    "host_env",
                    "Ambiente",
                    ["lab", "dev", "staging", "production"],
                    "Ambiente",
                    "lab",
                    False,
                ),
            ],
        },
    ),
    (
        "DESTROY-VM-LOCAL",
        {
            "name": "",
            "description": "destroy_vm.yml — desliga e remove VM no Fusion (vmrest); credenciais SSH + VMware REST no JT",
            "spec": [
                q_text(
                    "host_name",
                    "Nome do host (curto)",
                    "Ex: server10 — deve corresponder ao nome da VM no hypervisor",
                    "",
                    True,
                    128,
                ),
                q_text(
                    "host_domain",
                    "Domínio DNS",
                    "Sufixo do FQDN da VM",
                    "aroque.com.br",
                    False,
                    128,
                ),
            ],
        },
    ),
]


def project_id():
    r = api("GET", f"/projects/?organization=15&search={ORG_ROQUE_PROJECT}")
    if not r["count"]:
        raise SystemExit("Projeto ROQUE não encontrado")
    return r["results"][0]["id"]


def jt_id_by_name(pid, name):
    r = api("GET", f"/job_templates/?project={pid}&name={name}")
    if not r["count"]:
        return None
    return r["results"][0]["id"]


def apply_survey(jtid, body):
    api("POST", f"/job_templates/{jtid}/survey_spec/", body)
    api("PATCH", f"/job_templates/{jtid}/", {"survey_enabled": True})


def main():
    pid = project_id()
    for jt_name, survey in SURVEYS:
        jid = jt_id_by_name(pid, jt_name)
        if not jid:
            print(f"SKIP (não encontrado): {jt_name}", file=sys.stderr)
            continue
        apply_survey(jid, survey)
        print(f"OK survey: {jt_name} (JT id={jid})")
    print("Concluído.")


if __name__ == "__main__":
    main()
