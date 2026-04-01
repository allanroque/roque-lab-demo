#!/usr/bin/env python3
"""
Associa a label `cloud` a job templates e workflow templates de AWS/cloud
nas orgs SRE (2) e ROQUE (15). Idempotente.

Critério: nome do JT com prefixo AWS / WF-AWS, playbook em playbooks/aws/,
ou projeto com 'AWS' no nome (ex.: PROJ-GIT-AWS-ROQUE).

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


def ensure_label(org_id: int) -> int:
    r = api("GET", f"/labels/?organization={org_id}&name=cloud")
    if r["count"]:
        return r["results"][0]["id"]
    p = api("POST", "/labels/", {"name": "cloud", "organization": org_id})
    return p["id"]


def jt_is_cloud(row: dict) -> bool:
    name = (row.get("name") or "").upper()
    pb = (row.get("playbook") or "").replace("\\", "/").lower()
    proj = (row.get("summary_fields") or {}).get("project") or {}
    pname = (proj.get("name") or "").upper()
    if name in ("DEPLOY-NODEJS-LINUX", "NODEJS-DEPLOY-LINUX"):
        return True
    if name.startswith("AWS-") or name.startswith("WF-AWS"):
        return True
    if "AWS-" in name and "UPDATE" in name:
        return True
    if "/AWS/" in pb.upper() or "PLAYBOOKS/AWS/" in pb.upper():
        return True
    if "AWS" in pname and "PROJ-GIT" in pname:
        return True
    if name in (
        "DEPLOY-NODEJS-LINUX",
        "DEPLOY-APP-LINUX",
        "DEPLOY-NGINX-LINUX",
        "POSTGRES-DEPLOY-LINUX",
        "APACHE-DEPLOY-LINUX",
    ) and "AWS" in pname:
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


def associate_wf(wf_id: int, label_id: int):
    try:
        api("POST", f"/workflow_job_templates/{wf_id}/labels/", {"id": label_id})
    except urllib.error.HTTPError:
        pass


def main():
    if not TOKEN:
        print("Defina AAP_ADMIN_TOKEN", file=sys.stderr)
        sys.exit(1)

    for org_id in ORG_IDS:
        lid = ensure_label(org_id)
        print(f"Org {org_id}: label cloud id={lid}")

        jts = api("GET", f"/job_templates/?organization={org_id}&page_size=500")
        n = 0
        for row in jts.get("results", []):
            if jt_is_cloud(row):
                associate_jt(row["id"], lid)
                n += 1
                print(f"  JT {row['id']} {row['name']}")
        print(f"  Job templates etiquetados: {n}")

        wfs = api("GET", f"/workflow_job_templates/?organization={org_id}&page_size=500")
        m = 0
        for row in wfs.get("results", []):
            if wf_is_cloud(row):
                associate_wf(row["id"], lid)
                m += 1
                print(f"  WF {row['id']} {row['name']}")
        print(f"  Workflows etiquetados: {m}")


if __name__ == "__main__":
    main()
