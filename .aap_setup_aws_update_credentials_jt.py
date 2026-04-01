#!/usr/bin/env python3
"""
Cria CRED-AAP-SRE / CRED-AAP-ROQUE (tipo Red Hat Ansible Automation Platform),
Job Templates AWS-UPDATE-AAP-CREDENTIALS e survey (playbooks/aws/update_credentials.yml).

API deste script (Bearer): export AAP_ADMIN_TOKEN='<oauth admin>'

Conteúdo da credencial AAP usada pelo playbook (um dos modos):
  • OAuth: por defeito reutiliza AAP_ADMIN_TOKEN (ou defina AAP_CRED_OAUTH_TOKEN).
  • Utilizador/senha do controller: export AAP_CRED_USERNAME=admin
    e AAP_CRED_PASSWORD='...' (não grave senhas no repositório).

Opcional: AAP_CONTROLLER_HOST (default https://aap01.aroque.com.br)
"""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

TOKEN = os.environ.get("AAP_ADMIN_TOKEN", "").strip()
CONTROLLER_HOST = os.environ.get("AAP_CONTROLLER_HOST", "https://aap01.aroque.com.br").strip()
AAP_CRED_USER = os.environ.get("AAP_CRED_USERNAME", "").strip()
AAP_CRED_PASS = os.environ.get("AAP_CRED_PASSWORD", "").strip()
AAP_CRED_OAUTH = os.environ.get("AAP_CRED_OAUTH_TOKEN", "").strip()
BASE = f"{CONTROLLER_HOST.rstrip('/')}/api/controller/v2"

ORG_SRE = 2
ORG_ROQUE = 15
CRED_TYPE_AAP = 16
EE_DEFAULT = 4  # JT org SRE / default de projeto
EE_ROQUE_CLOUD = 13  # ee-demo-lab-roque — JT AWS-UPDATE-AAP-CREDENTIALS na org ROQUE
GIT_URL = "https://github.com/allanroque/roque-lab-demo.git"
GIT_BRANCH = "main"

PLAYBOOK = "playbooks/aws/update_credentials.yml"
JT_NAME = "AWS-UPDATE-AAP-CREDENTIALS"

SURVEY = {
    "name": "Credenciais AWS (Access Key)",
    "description": "Atualiza CRED-SSH-AWS-ROQUE e CRED-SSH-AWS-SRE no AAP.",
    "spec": [
        {
            "max": 2048,
            "min": 0,
            "type": "text",
            "choices": [],
            "default": "",
            "required": True,
            "variable": "aws_access_key_id",
            "question_name": "AWS Access Key ID",
            "question_description": "",
        },
        {
            "type": "password",
            "default": "",
            "required": True,
            "variable": "aws_secret_access_key",
            "question_name": "AWS Secret Access Key",
            "question_description": "",
        },
    ],
}

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


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


def ensure_project(org_id: int, name: str, sync_existing: bool = True) -> int:
    r = api("GET", f"/projects/?organization={org_id}&name={name}")
    if r["count"]:
        pid = r["results"][0]["id"]
        print(f"Projeto {name} org={org_id} id={pid}")
        if sync_existing:
            wait_project_sync(pid)
        return pid
    body = {
        "name": name,
        "description": "Repositório roque-lab-demo — automações",
        "organization": org_id,
        "scm_type": "git",
        "scm_url": GIT_URL,
        "scm_branch": GIT_BRANCH,
        "scm_clean": True,
        "scm_update_on_launch": True,
        "default_environment": EE_DEFAULT,
    }
    p = api("POST", "/projects/", body)
    print(f"Criado projeto {name} org={org_id} id={p['id']}")
    wait_project_sync(p["id"])
    return p["id"]


def _aap_credential_inputs():
    """Host + OAuth **ou** host + usuário/senha (mutuamente exclusivos no tipo AAP)."""
    base = {"host": CONTROLLER_HOST, "verify_ssl": False}
    if AAP_CRED_USER and AAP_CRED_PASS:
        base["username"] = AAP_CRED_USER
        base["password"] = AAP_CRED_PASS
        return base
    tok = AAP_CRED_OAUTH or TOKEN
    if not tok:
        raise SystemExit(
            "Para a credencial AAP: defina AAP_CRED_USERNAME+AAP_CRED_PASSWORD "
            "ou AAP_CRED_OAUTH_TOKEN / AAP_ADMIN_TOKEN (OAuth)."
        )
    base["oauth_token"] = tok
    return base


def ensure_aap_credential(org_id: int, name: str) -> int:
    r = api("GET", f"/credentials/?organization={org_id}&name={name}")
    if r["count"]:
        cid = r["results"][0]["id"]
        print(f"Credential {name} id={cid}")
        return cid
    body = {
        "name": name,
        "description": "API Red Hat Ansible Automation Platform para ansible.controller",
        "organization": org_id,
        "credential_type": CRED_TYPE_AAP,
        "inputs": _aap_credential_inputs(),
    }
    p = api("POST", "/credentials/", body)
    print(f"Criado {name} id={p['id']}")
    return p["id"]


def patch_aap_credential(cred_id: int):
    """Atualiza host/token ou usuário/senha (rotação)."""
    api(
        "PATCH",
        f"/credentials/{cred_id}/",
        {"inputs": _aap_credential_inputs()},
    )
    print(f"  Atualizada credential id={cred_id}")


def ensure_localhost_host(inventory_id: int):
    r = api("GET", f"/hosts/?inventory={inventory_id}&name=localhost")
    if r["count"]:
        return
    api("POST", "/hosts/", {"name": "localhost", "inventory": inventory_id, "enabled": True})
    print(f"  Adicionado host localhost ao inventário id={inventory_id}")


def ensure_label(org_id: int, name: str) -> int:
    r = api("GET", f"/labels/?organization={org_id}&name={name}")
    if r["count"]:
        return r["results"][0]["id"]
    p = api("POST", "/labels/", {"name": name, "organization": org_id})
    print(f"  Label {name} org={org_id} id={p['id']}")
    return p["id"]


def associate_cred(jt_id: int, cred_id: int):
    try:
        api("POST", f"/job_templates/{jt_id}/credentials/", {"id": cred_id})
    except urllib.error.HTTPError as e:
        err = e.read().decode() if e.fp else ""
        if e.code in (400, 204):
            # Já associada ou limite de credenciais do mesmo tipo
            return
        raise


def associate_label(jt_id: int, label_id: int):
    try:
        api("POST", f"/job_templates/{jt_id}/labels/", {"id": label_id})
    except urllib.error.HTTPError:
        pass


def upsert_jt(
    project_id: int,
    inventory_id: int,
    cred_id: int,
    label_ids: list[int],
    ee_id: int,
) -> int:
    body = {
        "name": JT_NAME,
        "description": "Atualiza CRED-SSH-AWS-ROQUE e CRED-SSH-AWS-SRE via survey (Access Key / Secret).",
        "job_type": "run",
        "inventory": inventory_id,
        "project": project_id,
        "playbook": PLAYBOOK,
        "verbosity": 1,
        "execution_environment": ee_id,
        "become_enabled": False,
        "diff_mode": False,
        "survey_enabled": True,
        "limit": "",
    }
    r = api("GET", f"/job_templates/?project={project_id}&name={JT_NAME}")
    if r["count"]:
        jtid = r["results"][0]["id"]
        api("PATCH", f"/job_templates/{jtid}/", body)
        print(f"Atualizado JT {JT_NAME} id={jtid}")
    else:
        p = api("POST", "/job_templates/", body)
        jtid = p["id"]
        print(f"Criado JT {JT_NAME} id={jtid}")
    associate_cred(jtid, cred_id)
    api("POST", f"/job_templates/{jtid}/survey_spec/", SURVEY)
    api("PATCH", f"/job_templates/{jtid}/", {"survey_enabled": True})
    for lid in label_ids:
        associate_label(jtid, lid)
    return jtid


def main():
    if not TOKEN:
        print(
            "Defina AAP_ADMIN_TOKEN para autenticar este script na API do controller.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("=== Credenciais AAP ===")
    cred_sre = ensure_aap_credential(ORG_SRE, "CRED-AAP-SRE")
    cred_roque = ensure_aap_credential(ORG_ROQUE, "CRED-AAP-ROQUE")
    patch_aap_credential(cred_sre)
    patch_aap_credential(cred_roque)

    print("=== Projetos Git roque-lab-demo ===")
    proj_sre = ensure_project(ORG_SRE, "PROJ-GIT-ROQUE-LAB")
    proj_roque = ensure_project(ORG_ROQUE, "PROJ-GIT-ROQUE-LAB")

    print("=== Inventário: localhost em ROQUE ===")
    ensure_localhost_host(26)

    print("=== Labels ===")
    lbl_aws_sre = ensure_label(ORG_SRE, "aws")
    lbl_cfg_sre = ensure_label(ORG_SRE, "config")
    lbl_cloud_sre = ensure_label(ORG_SRE, "cloud")
    lbl_aws_r = ensure_label(ORG_ROQUE, "aws")
    lbl_cfg_r = ensure_label(ORG_ROQUE, "config")
    lbl_cloud_r = ensure_label(ORG_ROQUE, "cloud")

    print("=== Job Templates ===")
    jt_sre = upsert_jt(
        proj_sre, 21, cred_sre, [lbl_aws_sre, lbl_cfg_sre, lbl_cloud_sre], EE_DEFAULT
    )
    jt_roque = upsert_jt(
        proj_roque,
        26,
        cred_roque,
        [lbl_aws_r, lbl_cfg_r, lbl_cloud_r],
        EE_ROQUE_CLOUD,
    )

    print("=== OK ===")
    print(f"  SRE:  JT id={jt_sre}  CRED-AAP-SRE id={cred_sre}  projeto id={proj_sre}  inv=INV-SRE-LAB (21)")
    print(f"  ROQUE: JT id={jt_roque} CRED-AAP-ROQUE id={cred_roque} projeto id={proj_roque} inv=INV-ROQUE-LAB (26)")


if __name__ == "__main__":
    main()
