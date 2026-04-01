#!/usr/bin/env python3
"""FASE 3B — Job templates e workflows AWS na org ROQUE (idempotente)."""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

TOKEN = os.environ.get("AAP_ADMIN_TOKEN", "").strip()
BASE = "https://aap01.aroque.com.br/api/controller/v2"
ORG_ID = 15
CRED_AWS = 36
CRED_SSH_AWS = 33
# ee-demo-lab-roque (quay.io/allanroque/ee-terraform:latest) — todos os JTs AWS/cloud ROQUE
EE_ROQUE_CLOUD = 13
INV_LAB = 26

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# Playbooks no repositório roque-lab-demo — projeto único PROJ-GIT-ROQUE-LAB

# Surveys alinhados aos playbooks em playbooks/aws/ e playbooks/linux/
SURVEYS = {
    "AWS-PROVISION-INFRA": {
        "name": "Infra AWS (VPC, SG, chave)",
        "description": "Variáveis para playbooks/aws/provision_infra.yml.",
        "spec": [
            {
                "max": 128,
                "min": 0,
                "type": "text",
                "default": "ansible-aws-lab",
                "required": False,
                "variable": "project_name",
                "question_name": "Nome do projeto (tag AWS)",
                "question_description": "Prefixo dos recursos (VPC, SG, key pair).",
            },
            {
                "type": "multiplechoice",
                "choices": "lab\ndev\nhml\nprod",
                "default": "lab",
                "required": False,
                "variable": "deploy_env",
                "question_name": "Ambiente (tag)",
                "question_description": "Tag Environment nos recursos.",
            },
            {
                "type": "multiplechoice",
                "choices": "us-east-2\nus-east-1\nus-west-1\nus-west-2\nsa-east-1",
                "default": "us-east-2",
                "required": False,
                "variable": "aws_region",
                "question_name": "Região AWS",
                "question_description": "",
            },
            {
                "max": 64,
                "min": 0,
                "type": "text",
                "default": "10.10.0.0/16",
                "required": False,
                "variable": "vpc_cidr",
                "question_name": "CIDR da VPC",
                "question_description": "",
            },
            {
                "max": 64,
                "min": 0,
                "type": "text",
                "default": "10.10.1.0/24",
                "required": False,
                "variable": "public_subnet_cidr",
                "question_name": "CIDR da subnet pública",
                "question_description": "",
            },
            {
                "max": 4096,
                "min": 0,
                "type": "text",
                "default": "",
                "required": False,
                "variable": "ec2_ssh_public_key",
                "question_name": "Chave pública SSH (RSA)",
                "question_description": "Conteúdo da chave pública para importar no AWS.",
            },
        ],
    },
    "AWS-PROVISION-EC2": {
        "name": "Provisionamento EC2 RHEL",
        "description": "Variáveis para playbooks/aws/provision_ec2.yml (infra já existente).",
        "spec": [
            {
                "max": 128,
                "min": 1,
                "type": "text",
                "default": "server",
                "required": True,
                "variable": "ec2_server_name",
                "question_name": "Nome base das instâncias",
                "question_description": "Ex.: quantidade 3 → server1, server2, server3.",
            },
            {
                "type": "multiplechoice",
                "choices": "t2.micro\nt2.small\nt2.medium",
                "default": "t2.micro",
                "required": True,
                "variable": "ec2_instance_size",
                "question_name": "Tamanho da instância",
                "question_description": "",
            },
            {
                "max": 100,
                "min": 1,
                "type": "integer",
                "default": 1,
                "required": True,
                "variable": "ec2_quantity",
                "question_name": "Quantidade",
                "question_description": "Número de instâncias (≥ 1).",
            },
            {
                "type": "multiplechoice",
                "choices": "webserver\ndatabase\napache\nnginx\npostgres\ninfraserver\napp",
                "default": "webserver",
                "required": True,
                "variable": "ec2_server_role",
                "question_name": "Tag Role",
                "question_description": "Papel / função da instância (tag Role).",
            },
            {
                "type": "multiplechoice",
                "choices": "lab\ndev\nhml\nprod",
                "default": "lab",
                "required": True,
                "variable": "ec2_server_group",
                "question_name": "Tag Group",
                "question_description": "Grupo lógico / ambiente (tag Group).",
            },
            {
                "type": "multiplechoice",
                "choices": "us-east-2\nus-east-1\nus-west-1\nus-west-2\nsa-east-1",
                "default": "us-east-2",
                "required": False,
                "variable": "aws_region",
                "question_name": "Região AWS",
                "question_description": "Deve ser a mesma região da infra.",
            },
        ],
    },
    "AWS-TEARDOWN": {
        "name": "Teardown AWS",
        "description": "Variáveis para playbooks/aws/teardown.yml. confirm_destroy deve ser yes.",
        "spec": [
            {
                "max": 32,
                "min": 1,
                "type": "text",
                "default": "no",
                "required": True,
                "variable": "confirm_destroy",
                "question_name": "Confirmar destruição",
                "question_description": "Digite yes para confirmar. Qualquer outro valor falha o job.",
            },
            {
                "max": 128,
                "min": 0,
                "type": "text",
                "default": "ansible-aws-lab",
                "required": False,
                "variable": "project_name",
                "question_name": "Nome do projeto",
                "question_description": "Deve coincidir com o usado no provision_infra.",
            },
            {
                "type": "multiplechoice",
                "choices": "us-east-2\nus-east-1\nus-west-1\nus-west-2\nsa-east-1",
                "default": "us-east-2",
                "required": False,
                "variable": "aws_region",
                "question_name": "Região AWS",
                "question_description": "Região onde os recursos serão destruídos.",
            },
        ],
    },
    "POSTGRES-DEPLOY-LINUX": {
        "name": "Configure PostgreSQL",
        "description": "Parâmetros do banco (playbooks/linux/database/deploy_postgres.yml).",
        "spec": [
            {
                "max": 128,
                "min": 1,
                "type": "text",
                "default": "appdb",
                "required": True,
                "variable": "postgres_db_name",
                "question_name": "Database Name",
                "question_description": "Nome do banco de dados a criar.",
            },
            {
                "max": 128,
                "min": 1,
                "type": "text",
                "default": "appuser",
                "required": True,
                "variable": "postgres_db_user",
                "question_name": "Database User",
                "question_description": "Usuário da aplicação no PostgreSQL.",
            },
            {
                "type": "password",
                "default": "",
                "required": True,
                "variable": "postgres_db_password",
                "question_name": "Database Password",
                "question_description": "Senha do usuário (não é exibida em claro nos logs).",
            },
            {
                "max": 65535,
                "min": 1,
                "type": "integer",
                "default": 5432,
                "required": False,
                "variable": "postgres_port",
                "question_name": "Port",
                "question_description": "Porta de escuta do PostgreSQL.",
            },
        ],
    },
    "APACHE-DEPLOY-LINUX": {
        "name": "Configure Apache",
        "description": "Apache httpd (playbooks/linux/apache/deploy_apache_rhel.yml).",
        "spec": [
            {
                "max": 65535,
                "min": 1,
                "type": "integer",
                "default": 80,
                "required": False,
                "variable": "apache_port",
                "question_name": "Port",
                "question_description": "Porta de escuta do httpd.",
            }
        ],
    },
    "DEPLOY-NGINX-LINUX": {
        "name": "Configure Nginx",
        "description": "Nginx (playbooks/linux/nginx/configure_nginx.yml).",
        "spec": [
            {
                "max": 65535,
                "min": 1,
                "type": "integer",
                "default": 80,
                "required": False,
                "variable": "nginx_port",
                "question_name": "Port",
                "question_description": "Porta de escuta do Nginx.",
            }
        ],
    },
    "DEPLOY-APP-LINUX": {
        "name": "DEPLOY-APP-LINUX",
        "description": "Flask (playbooks/linux/app/deploy_flask_app.yml).",
        "spec": [
            {
                "max": 128,
                "min": 1,
                "type": "text",
                "default": "myapp",
                "required": True,
                "variable": "app_name",
                "question_name": "App Name",
                "question_description": "Nome do serviço systemd e identificador.",
            },
            {
                "max": 65535,
                "min": 1,
                "type": "integer",
                "default": 8080,
                "required": False,
                "variable": "app_port",
                "question_name": "Port",
                "question_description": "Porta TCP da aplicação.",
            },
            {
                "type": "multiplechoice",
                "choices": "development\nstaging\nproduction",
                "default": "production",
                "required": False,
                "variable": "app_env",
                "question_name": "Environment",
                "question_description": "Rótulo de ambiente (variável app_env).",
            },
        ],
    },
    "DEPLOY-NODEJS-LINUX": {
        "name": "Deploy Node.js",
        "description": "Node.js (playbooks/linux/nodejs/deploy_nodejs.yml).",
        "spec": [
            {
                "max": 128,
                "min": 1,
                "type": "text",
                "default": "myapp",
                "required": True,
                "variable": "app_name",
                "question_name": "App Name",
                "question_description": "Nome do serviço systemd e diretório em /opt.",
            },
            {
                "max": 65535,
                "min": 1,
                "type": "integer",
                "default": 3000,
                "required": False,
                "variable": "app_port",
                "question_name": "Port",
                "question_description": "Porta TCP.",
            },
            {
                "type": "multiplechoice",
                "choices": "development\nstaging\nproduction",
                "default": "production",
                "required": False,
                "variable": "app_env",
                "question_name": "Environment",
                "question_description": "NODE_ENV.",
            },
        ],
    },
}


def api(method: str, path: str, data=None):
    url = BASE + path
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }
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


def wait_project_sync(project_id: int, timeout: int = 300):
    api("POST", f"/projects/{project_id}/update/", {})
    for _ in range(timeout // 3):
        r = api(
            "GET",
            f"/projects/{project_id}/project_updates/?order_by=-created&page_size=1",
        )
        if not r["count"]:
            time.sleep(2)
            continue
        st = r["results"][0].get("status")
        if st == "successful":
            print(f"  Projeto {project_id} sync OK")
            return
        if st == "failed":
            raise SystemExit(f"Falha no sync do projeto {project_id}")
        time.sleep(3)
    raise SystemExit("Timeout aguardando sync do projeto")


def ensure_label(name: str) -> int:
    r = api("GET", f"/labels/?organization={ORG_ID}&name={name}")
    if r["count"]:
        return r["results"][0]["id"]
    p = api("POST", "/labels/", {"name": name, "organization": ORG_ID})
    print(f"Label {name} id={p['id']}")
    return p["id"]


def ensure_roque_lab_project() -> int:
    """Repositório único: github.com/allanroque/roque-lab-demo (main)."""
    r = api("GET", f"/projects/?organization={ORG_ID}&name=PROJ-GIT-ROQUE-LAB")
    if not r["count"]:
        raise SystemExit(
            "Projeto PROJ-GIT-ROQUE-LAB não encontrado. Execute .aap_bootstrap_roque.py primeiro."
        )
    pid = r["results"][0]["id"]
    print(f"Projeto PROJ-GIT-ROQUE-LAB id={pid}")
    wait_project_sync(pid)
    return pid


def jt_id_by_org_name(name: str):
    r = api("GET", f"/job_templates/?organization={ORG_ID}&name={name}")
    return r["results"][0]["id"] if r["count"] else None


def associate_cred(jt_id: int, cred_id: int):
    try:
        api("POST", f"/job_templates/{jt_id}/credentials/", {"id": cred_id})
    except urllib.error.HTTPError as e:
        if e.code in (400, 204):
            return
        raise


def associate_label(jt_id: int, label_id: int):
    try:
        api("POST", f"/job_templates/{jt_id}/labels/", {"id": label_id})
    except urllib.error.HTTPError:
        pass


def associate_wf_label(wf_id: int, label_id: int):
    try:
        api("POST", f"/workflow_job_templates/{wf_id}/labels/", {"id": label_id})
    except urllib.error.HTTPError:
        pass


def default_limit_for_jt(name: str) -> str:
    """Grupo do inventário (limit); vazio para API/localhost (AWS, DNS, IPAM)."""
    if name.startswith("AWS-"):
        return ""
    if name.startswith("DNS-") or name.startswith("IPAM-"):
        return ""
    if name == "POSTGRES-DEPLOY-LINUX":
        return "postgresql"
    if name == "APACHE-DEPLOY-LINUX":
        return "apache"
    if name == "DEPLOY-NGINX-LINUX":
        return "nginx"
    if name in ("DEPLOY-APP-LINUX", "DEPLOY-NODEJS-LINUX"):
        return "app"
    return "infra"


def upsert_jt(
    project_id: int,
    name: str,
    playbook: str,
    inventory_id: int,
    ee_id: int,
    become: bool,
    creds: list[int],
    label_ids: list[int],
) -> int:
    body = {
        "name": name,
        "description": "",
        "job_type": "run",
        "inventory": inventory_id,
        "project": project_id,
        "playbook": playbook,
        "verbosity": 1,
        "execution_environment": ee_id,
        "become_enabled": become,
        "diff_mode": True,
        "survey_enabled": name in SURVEYS,
        "limit": default_limit_for_jt(name),
    }
    existing = jt_id_by_org_name(name)
    if existing:
        p = api("PATCH", f"/job_templates/{existing}/", body)
        jtid = existing
        print(f"  Atualizado JT {name} id={jtid}")
    else:
        p = api("POST", "/job_templates/", body)
        jtid = p["id"]
        print(f"  Criado JT {name} id={jtid}")
    for c in creds:
        associate_cred(jtid, c)
    for lid in label_ids:
        associate_label(jtid, lid)
    if name in SURVEYS:
        api("POST", f"/job_templates/{jtid}/survey_spec/", SURVEYS[name])
        api("PATCH", f"/job_templates/{jtid}/", {"survey_enabled": True})
    return jtid


def wf_exists(name: str):
    r = api("GET", f"/workflow_job_templates/?organization={ORG_ID}&name={name}")
    return r["results"][0]["id"] if r["count"] else None


def create_workflow(name: str, jt_by_name_map: dict, chain: list[str]):
    wfid = wf_exists(name)
    if wfid:
        print(f"Workflow {name} já existe id={wfid} — mantendo nós existentes.")
        return wfid
    wf = api(
        "POST",
        "/workflow_job_templates/",
        {"name": name, "description": "", "organization": ORG_ID},
    )
    wfid = wf["id"]
    print(f"Criado workflow {name} id={wfid}")
    nodes = []
    for jtname in chain:
        jid = jt_by_name_map[jtname]
        n = api(
            "POST",
            "/workflow_job_template_nodes/",
            {
                "workflow_job_template": wfid,
                "unified_job_template": jid,
            },
        )
        nodes.append(n["id"])
    for i in range(len(nodes) - 1):
        api(
            "POST",
            f"/workflow_job_template_nodes/{nodes[i]}/success_nodes/",
            {"id": nodes[i + 1]},
        )
    return wfid


def main():
    if not TOKEN:
        print("Defina AAP_ADMIN_TOKEN", file=sys.stderr)
        sys.exit(1)

    print("=== 1) Projeto PROJ-GIT-ROQUE-LAB (inventário: INV-ROQUE-LAB) ===")
    lab_pid = ensure_roque_lab_project()

    label_aws = ensure_label("aws")
    label_cloud = ensure_label("cloud")
    label_deploy = ensure_label("deploy")
    label_linux = ensure_label("linux")

    print("=== 2) Job templates (playbooks no roque-lab-demo) ===")
    jt_ids = {}

    jt_ids["AWS-PROVISION-INFRA"] = upsert_jt(
        lab_pid,
        "AWS-PROVISION-INFRA",
        "playbooks/aws/provision_infra.yml",
        INV_LAB,
        EE_ROQUE_CLOUD,
        False,
        [CRED_AWS],
        [label_aws, label_cloud],
    )

    jt_ids["AWS-PROVISION-EC2"] = upsert_jt(
        lab_pid,
        "AWS-PROVISION-EC2",
        "playbooks/aws/provision_ec2.yml",
        INV_LAB,
        EE_ROQUE_CLOUD,
        False,
        [CRED_AWS, CRED_SSH_AWS],
        [label_aws, label_cloud],
    )

    jt_ids["AWS-TEARDOWN"] = upsert_jt(
        lab_pid,
        "AWS-TEARDOWN",
        "playbooks/aws/teardown.yml",
        INV_LAB,
        EE_ROQUE_CLOUD,
        False,
        [CRED_AWS],
        [label_aws, label_cloud],
    )

    jt_ids["POSTGRES-DEPLOY-LINUX"] = upsert_jt(
        lab_pid,
        "POSTGRES-DEPLOY-LINUX",
        "playbooks/linux/database/deploy_postgres.yml",
        INV_LAB,
        EE_ROQUE_CLOUD,
        True,
        [CRED_SSH_AWS],
        [label_deploy, label_linux],
    )

    jt_ids["APACHE-DEPLOY-LINUX"] = upsert_jt(
        lab_pid,
        "APACHE-DEPLOY-LINUX",
        "playbooks/linux/apache/deploy_apache_rhel.yml",
        INV_LAB,
        EE_ROQUE_CLOUD,
        True,
        [CRED_SSH_AWS],
        [label_deploy, label_linux],
    )

    jt_ids["DEPLOY-NGINX-LINUX"] = upsert_jt(
        lab_pid,
        "DEPLOY-NGINX-LINUX",
        "playbooks/linux/nginx/configure_nginx.yml",
        INV_LAB,
        EE_ROQUE_CLOUD,
        True,
        [CRED_SSH_AWS],
        [label_deploy, label_linux],
    )

    jt_ids["DEPLOY-APP-LINUX"] = upsert_jt(
        lab_pid,
        "DEPLOY-APP-LINUX",
        "playbooks/linux/app/deploy_flask_app.yml",
        INV_LAB,
        EE_ROQUE_CLOUD,
        True,
        [CRED_SSH_AWS],
        [label_deploy, label_linux],
    )

    jt_ids["DEPLOY-NODEJS-LINUX"] = upsert_jt(
        lab_pid,
        "DEPLOY-NODEJS-LINUX",
        "playbooks/linux/nodejs/deploy_nodejs.yml",
        INV_LAB,
        EE_ROQUE_CLOUD,
        True,
        [CRED_SSH_AWS],
        [label_deploy, label_linux],
    )

    print("=== 3) Workflows ===")
    full_chain = [
        "AWS-PROVISION-INFRA",
        "AWS-PROVISION-EC2",
        "POSTGRES-DEPLOY-LINUX",
        "APACHE-DEPLOY-LINUX",
        "DEPLOY-NGINX-LINUX",
        "DEPLOY-APP-LINUX",
        "DEPLOY-NODEJS-LINUX",
    ]
    create_workflow("WF-AWS-FULL-DEPLOYMENT", jt_ids, full_chain)
    create_workflow("WF-AWS-TEARDOWN-CLEANUP", jt_ids, ["AWS-TEARDOWN"])

    print("=== 4) Labels cloud nos workflows AWS ===")
    for wf_name in ("WF-AWS-FULL-DEPLOYMENT", "WF-AWS-TEARDOWN-CLEANUP"):
        wfid = wf_exists(wf_name)
        if wfid:
            associate_wf_label(wfid, label_aws)
            associate_wf_label(wfid, label_cloud)

    print("=== Concluído ===")
    for k, v in jt_ids.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
