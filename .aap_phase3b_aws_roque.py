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

# Mapeamento SRE → nomes ROQUE (playbooks repo ansible-lab-aws-cloud)
AWS_PROJECT = {
    "name": "PROJ-GIT-AWS-ROQUE",
    "description": "AWS / cloud — espelho SRE (ansible-lab-aws-cloud)",
    "organization": ORG_ID,
    "scm_type": "git",
    "scm_url": "https://github.com/allanroque/ansible-lab-aws-cloud.git",
    "scm_branch": "main",
    "scm_clean": True,
    "scm_update_on_launch": True,
        "default_environment": EE_ROQUE_CLOUD,
}

DR_PROJECT = {
    "name": "PROJ-GIT-DR-ROQUE",
    "description": "DR — deploy backend Node (espelho ansible-lab-dr)",
    "organization": ORG_ID,
    "scm_type": "git",
    "scm_url": "https://github.com/allanroque/ansible-lab-dr.git",
    "scm_branch": "main",
    "scm_clean": True,
    "scm_update_on_launch": True,
        "default_environment": EE_ROQUE_CLOUD,
}

# Surveys copiados dos job templates SRE (270, 272, 271, 274–277)
SURVEYS = {
    "AWS-PROVISION-INFRA": {
        "name": "Infra AWS (rede + SG + chave)",
        "description": "Variáveis para playbooks/provisioning-aws-infra.yml.",
        "spec": [
            {
                "type": "multiplechoice",
                "choices": "us-east-2\nus-east-1\nus-west-1\nus-west-2\nsa-east-1",
                "default": "us-east-2",
                "required": False,
                "variable": "aws_region",
                "question_name": "Região AWS",
                "question_description": "Região AWS onde o ambiente será criado.",
            },
            {
                "max": 128,
                "min": 0,
                "type": "text",
                "default": "lab",
                "required": False,
                "variable": "environment",
                "question_name": "Ambiente (tag)",
                "question_description": "Tag de ambiente aplicada em todos os recursos.",
            },
        ],
    },
    "AWS-PROVISION-EC2": {
        "name": "Provisionamento EC2 RHEL",
        "description": "Variáveis para playbooks/provisioning-aws-ec2.yml (infra já existente).",
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
        "description": "Variáveis para playbooks/teardown-aws.yml. confirm_destroy deve ser yes para executar.",
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
        "description": "Parâmetros do banco (configure-postgres.yml).",
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
        "description": "Porta HTTP do Apache (configure-apache.yml).",
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
        "description": "Porta HTTP do Nginx (configure-nginx.yml).",
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
        "description": "Parâmetros para configure-app.yml (deploy via templates da role app, sem repositório Git).",
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


def find_project(name: str):
    r = api("GET", f"/projects/?organization={ORG_ID}&search={name}")
    return r["results"][0]["id"] if r["count"] else None


def ensure_inventory(name: str, description: str) -> int:
    r = api("GET", f"/inventories/?organization={ORG_ID}&name={name}")
    if r["count"]:
        iid = r["results"][0]["id"]
        print(f"Inventário {name} id={iid}")
        return iid
    p = api(
        "POST",
        "/inventories/",
        {"name": name, "description": description, "organization": ORG_ID},
    )
    print(f"Criado inventário {name} id={p['id']}")
    return p["id"]


def ensure_label(name: str) -> int:
    r = api("GET", f"/labels/?organization={ORG_ID}&name={name}")
    if r["count"]:
        return r["results"][0]["id"]
    p = api("POST", "/labels/", {"name": name, "organization": ORG_ID})
    print(f"Label {name} id={p['id']}")
    return p["id"]


def rename_apache_v1():
    """Libera o nome APACHE-DEPLOY-LINUX para o playbook AWS (configure-apache.yml)."""
    r = api("GET", f"/job_templates/?organization={ORG_ID}&name=APACHE-DEPLOY-LINUX")
    if not r["count"]:
        print("JT APACHE-DEPLOY-LINUX não encontrado — skip rename.")
        return
    jt = r["results"][0]
    if jt["name"] != "APACHE-DEPLOY-LINUX":
        return
    pb = jt.get("playbook") or ""
    if "deploy_apache_rhel" not in pb:
        print("APACHE-DEPLOY-LINUX já não é o playbook RHEL — skip rename.")
        return
    r2 = api("GET", f"/job_templates/?organization={ORG_ID}&name=APACHE-DEPLOY-LINUX-V1")
    if r2["count"]:
        print("APACHE-DEPLOY-LINUX-V1 já existe — ajuste manual se necessário.")
        return
    api("PATCH", f"/job_templates/{jt['id']}/", {"name": "APACHE-DEPLOY-LINUX-V1"})
    print(f"Renomeado JT id={jt['id']} → APACHE-DEPLOY-LINUX-V1 (playbook RHEL).")


def ensure_aws_project() -> int:
    pid = find_project("PROJ-GIT-AWS-ROQUE")
    if pid:
        print(f"Projeto PROJ-GIT-AWS-ROQUE id={pid}")
        return pid
    p = api("POST", "/projects/", AWS_PROJECT)
    pid = p["id"]
    print(f"Criado PROJ-GIT-AWS-ROQUE id={pid}")
    wait_project_sync(pid)
    return pid


def ensure_dr_project() -> int:
    pid = find_project("PROJ-GIT-DR-ROQUE")
    if pid:
        print(f"Projeto PROJ-GIT-DR-ROQUE id={pid}")
        return pid
    p = api("POST", "/projects/", DR_PROJECT)
    pid = p["id"]
    print(f"Criado PROJ-GIT-DR-ROQUE id={pid}")
    wait_project_sync(pid)
    return pid


def jt_by_name(project_id: int, name: str):
    r = api("GET", f"/job_templates/?project={project_id}&name={name}")
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
    }
    existing = jt_by_name(project_id, name)
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

    print("=== 1) Renomear APACHE RHEL → APACHE-DEPLOY-LINUX-V1 ===")
    rename_apache_v1()

    print("=== 2) Inventário INV-AWS-ROQUE ===")
    inv_aws = ensure_inventory("INV-AWS-ROQUE", "Alvos EC2 / apps AWS (org ROQUE)")

    print("=== 3) Projetos SCM ===")
    aws_pid = ensure_aws_project()
    dr_pid = ensure_dr_project()

    label_aws = ensure_label("aws")
    label_cloud = ensure_label("cloud")
    label_deploy = ensure_label("deploy")
    label_linux = ensure_label("linux")

    print("=== 4) Job templates (PROJ-GIT-AWS-ROQUE) ===")
    jt_ids = {}

    jt_ids["AWS-PROVISION-INFRA"] = upsert_jt(
        aws_pid,
        "AWS-PROVISION-INFRA",
        "playbooks/provisioning-aws-infra.yml",
        INV_LAB,
        EE_ROQUE_CLOUD,
        False,
        [CRED_AWS],
        [label_aws, label_cloud],
    )

    jt_ids["AWS-PROVISION-EC2"] = upsert_jt(
        aws_pid,
        "AWS-PROVISION-EC2",
        "playbooks/provisioning-aws-ec2.yml",
        INV_LAB,
        EE_ROQUE_CLOUD,
        False,
        [CRED_AWS, CRED_SSH_AWS],
        [label_aws, label_cloud],
    )

    jt_ids["AWS-TEARDOWN"] = upsert_jt(
        aws_pid,
        "AWS-TEARDOWN",
        "playbooks/teardown-aws.yml",
        INV_LAB,
        EE_ROQUE_CLOUD,
        False,
        [CRED_AWS],
        [label_aws, label_cloud],
    )

    jt_ids["POSTGRES-DEPLOY-LINUX"] = upsert_jt(
        aws_pid,
        "POSTGRES-DEPLOY-LINUX",
        "playbooks/configure-postgres.yml",
        inv_aws,
        EE_ROQUE_CLOUD,
        True,
        [CRED_SSH_AWS],
        [label_deploy, label_linux],
    )

    jt_ids["APACHE-DEPLOY-LINUX"] = upsert_jt(
        aws_pid,
        "APACHE-DEPLOY-LINUX",
        "playbooks/configure-apache.yml",
        inv_aws,
        EE_ROQUE_CLOUD,
        True,
        [CRED_SSH_AWS],
        [label_deploy, label_linux],
    )

    jt_ids["DEPLOY-NGINX-LINUX"] = upsert_jt(
        aws_pid,
        "DEPLOY-NGINX-LINUX",
        "playbooks/configure-nginx.yml",
        INV_LAB,
        EE_ROQUE_CLOUD,
        True,
        [CRED_SSH_AWS],
        [label_deploy, label_linux],
    )

    jt_ids["DEPLOY-APP-LINUX"] = upsert_jt(
        aws_pid,
        "DEPLOY-APP-LINUX",
        "playbooks/configure-app.yml",
        inv_aws,
        EE_ROQUE_CLOUD,
        True,
        [CRED_SSH_AWS],
        [label_deploy, label_linux],
    )

    print("=== 5) DEPLOY-NODEJS-LINUX (PROJ-GIT-DR-ROQUE) ===")
    body_node = {
        "name": "DEPLOY-NODEJS-LINUX",
        "description": "Espelho SRE NODEJS-DEPLOY-LINUX (deploy-backend.yml)",
        "job_type": "run",
        "inventory": inv_aws,
        "project": dr_pid,
        "playbook": "deploy-backend.yml",
        "verbosity": 1,
        "execution_environment": EE_ROQUE_CLOUD,
        "become_enabled": True,
        "diff_mode": True,
        "survey_enabled": False,
    }
    ex = jt_by_name(dr_pid, "DEPLOY-NODEJS-LINUX")
    if ex:
        api("PATCH", f"/job_templates/{ex}/", body_node)
        nj = ex
        print(f"  Atualizado DEPLOY-NODEJS-LINUX id={nj}")
    else:
        p = api("POST", "/job_templates/", body_node)
        nj = p["id"]
        print(f"  Criado DEPLOY-NODEJS-LINUX id={nj}")
    associate_cred(nj, CRED_SSH_AWS)
    for lid in (label_deploy, label_linux):
        associate_label(nj, lid)
    jt_ids["DEPLOY-NODEJS-LINUX"] = nj

    print("=== 6) Workflows ===")
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

    print("=== 7) Labels cloud nos workflows AWS ===")
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
