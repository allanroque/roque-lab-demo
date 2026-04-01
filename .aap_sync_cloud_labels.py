#!/usr/bin/env python3
"""
Associa a label `cloud` a job templates e workflows focados em AWS (API, provisão,
credenciais, teardown). Não aplica a templates de stack Linux (Apache, Nginx, etc.).

Remove `aws` e `cloud` de JTs de deploy Linux (mesmos nomes em SRE/ROQUE).

Requer: AAP_ADMIN_TOKEN
"""
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

TOKEN = os.environ.get("AAP_ADMIN_TOKEN", "").strip()
CONTROLLER_HOST = os.environ.get("AAP_CONTROLLER_HOST", "https://aap01.aroque.com.br").strip()
BASE = f"{CONTROLLER_HOST.rstrip('/')}/api/controller/v2"
ORG_IDS = [2, 15]

# JTs de configuração de serviços Linux (não são automações “AWS” no sentido de control plane)
JT_NAMES_LINUX_STACK_ONLY = frozenset(
    {
        "POSTGRES-DEPLOY-LINUX",
        "APACHE-DEPLOY-LINUX",
        "DEPLOY-NGINX-LINUX",
        "DEPLOY-APP-LINUX",
        "DEPLOY-NODEJS-LINUX",
        "NODEJS-DEPLOY-LINUX",
    }
)

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
    with urllib.request.urlopen(req, context=CTX, timeout=120) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else {}


def ensure_label(org_id: int, name: str) -> int:
    r = api("GET", f"/labels/?organization={org_id}&name={name}")
    if r["count"]:
        return r["results"][0]["id"]
    p = api("POST", "/labels/", {"name": name, "organization": org_id})
    return p["id"]


def jt_is_cloud(row: dict) -> bool:
    """Apenas JTs focados em AWS (provisão, teardown, credenciais, S3, etc.)."""
    name = row.get("name") or ""
    if name in JT_NAMES_LINUX_STACK_ONLY:
        return False
    u = name.upper()
    pb = (row.get("playbook") or "").replace("\\", "/").lower()
    if u.startswith("AWS-") or ("AWS-" in u and "UPDATE" in u):
        return True
    if "aws-s3" in pb or "s3-backend" in pb or "setup-s3-backend" in pb:
        return True
    if "provisioning-aws" in pb or "teardown-aws" in pb:
        return True
    if "playbooks/aws/update_credentials" in pb or "playbooks/aws/provision" in pb:
        return True
    if "playbooks/aws/teardown" in pb:
        return True
    return False


def wf_is_cloud(row: dict) -> bool:
    name = (row.get("name") or "").upper()
    return "AWS" in name or name.startswith("WF-AWS")


def associate_jt(jt_id: int, label_id: int):
    try:
        api("POST", f"/job_templates/{jt_id}/labels/", {"id": label_id})
    except urllib.error.HTTPError:
        pass


def disassociate_jt_label(jt_id: int, label_id: int):
    try:
        api(
            "POST",
            f"/job_templates/{jt_id}/labels/",
            {"id": label_id, "disassociate": True},
        )
    except urllib.error.HTTPError:
        pass


def associate_wf(wf_id: int, label_id: int):
    try:
        api("POST", f"/workflow_job_templates/{wf_id}/labels/", {"id": label_id})
    except urllib.error.HTTPError:
        pass


def strip_aws_cloud_from_linux_stack_jts(org_id: int):
    """Remove labels aws e cloud dos JTs de stack Linux (deploy em VM)."""
    for lbl_name in ("aws", "cloud"):
        r = api("GET", f"/labels/?organization={org_id}&name={lbl_name}")
        if not r["count"]:
            continue
        lid = r["results"][0]["id"]
        jts = api("GET", f"/job_templates/?organization={org_id}&page_size=500")
        for row in jts.get("results", []):
            if (row.get("name") or "") not in JT_NAMES_LINUX_STACK_ONLY:
                continue
            disassociate_jt_label(row["id"], lid)
            print(f"  removido {lbl_name}: JT {row['id']} {row['name']}")


def main():
    if not TOKEN:
        print("Defina AAP_ADMIN_TOKEN", file=sys.stderr)
        sys.exit(1)

    for org_id in ORG_IDS:
        print(f"=== Org {org_id}: remover aws/cloud de JTs Linux stack ===")
        strip_aws_cloud_from_linux_stack_jts(org_id)

        lid = ensure_label(org_id, "cloud")
        print(f"Org {org_id}: label cloud id={lid}")

        jts = api("GET", f"/job_templates/?organization={org_id}&page_size=500")
        n = 0
        for row in jts.get("results", []):
            if jt_is_cloud(row):
                associate_jt(row["id"], lid)
                n += 1
                print(f"  JT {row['id']} {row['name']}")
        print(f"  Job templates com label cloud: {n}")

        wfs = api("GET", f"/workflow_job_templates/?organization={org_id}&page_size=500")
        m = 0
        for row in wfs.get("results", []):
            if wf_is_cloud(row):
                associate_wf(row["id"], lid)
                m += 1
                print(f"  WF {row['id']} {row['name']}")
        print(f"  Workflows com label cloud: {m}")


if __name__ == "__main__":
    main()
