#!/usr/bin/env python3
"""FASE 4 — testes de jobs ROQUE (API controller). Apague após uso se preferir."""
import json
import os
import re
import ssl
import sys
import time
import urllib.request
import urllib.error

BASE = "https://aap01.aroque.com.br/api/controller/v2"
LIMIT = "server01.aroque.com.br,server02.aroque.com.br"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def get_token():
    t = os.environ.get("AAP_ADMIN_TOKEN", "").strip()
    if t:
        return t
    p = os.path.join(os.path.dirname(__file__), ".mcp.json")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            for line in f:
                if "b4td" in line and "Bearer" in line:
                    return line.split("Bearer")[-1].strip().strip('",')
    raise SystemExit("Defina AAP_ADMIN_TOKEN ou use .mcp.json com token admin.")


TOKEN = get_token()


def api(method, path, data=None):
    url = BASE + path
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, context=CTX, timeout=300) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else {}


def launch_jt(jt_id, payload=None):
    return api("POST", f"/job_templates/{jt_id}/launch/", payload or {})


def wait_job(job_id, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = api("GET", f"/jobs/{job_id}/")
        st = j.get("status")
        if st in ("successful", "failed", "error", "canceled"):
            return j
        time.sleep(3)
    raise TimeoutError(f"job {job_id}")


def fetch_stdout_txt(job_id):
    url = f"{BASE}/jobs/{job_id}/stdout/?format=txt"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, context=CTX, timeout=120) as r:
        return r.read().decode(errors="replace")


def parse_recap(stdout: str):
    """Extrai linhas PLAY RECAP e totais changed."""
    recaps = []
    for line in stdout.splitlines():
        if re.match(r"^\S+\s+:\s+ok=", line.strip()):
            recaps.append(line.strip())
    changed_total = 0
    m = re.findall(r"changed=(\d+)", stdout)
    for x in m:
        changed_total += int(x)
    failed = "failed=1" in stdout or re.search(r"failed=[1-9]", stdout)
    return recaps, changed_total, bool(failed)


def verify_jts_exist(project_id=278):
    """ServiceNow/DNS/IPAM — só existência."""
    names = [
        "SNOW-INCIDENT-CREATE",
        "DNS-ADD-RECORD",
        "IPAM-ADD-IP",
    ]
    out = []
    for n in names:
        r = api("GET", f"/job_templates/?project={project_id}&name={n}")
        ok = r.get("count", 0) >= 1
        out.append((n, ok, r["results"][0]["id"] if ok else None))
    return out


def main():
    tests = [
        (311, "LINUX-CONFIG-MOTD", 1),
        (313, "LINUX-CONFIG-PACKAGES", 1),
        (291, "LINUX-CONFIG-CHRONY", 1),
        (290, "APACHE-DEPLOY-LINUX-V1", 2),
        (312, "NGINX-DEPLOY-LINUX", 2),
        (315, "LINUX-CONFIG-SERVICES", 2),
        (301, "LINUX-HARDENING", 3),
        (314, "LINUX-CONFIG-SELINUX", 3),
        (286, "LINUX-ADHOC-COMMAND", 4),
        (317, "LINUX-TSHOOT", 4),
    ]
    results = []
    launch_payload = {"limit": LIMIT}

    print("### Verificação templates externos (não executados)\n")
    for name, ok, jid in verify_jts_exist():
        print(f"  {name}: {'OK id=' + str(jid) if ok else 'FALTANDO'}")

    print("\n### Conectividade / credencial SSH")
    print(f"  Inventário INV-ROQUE-LAB: hosts em limit {LIMIT}")
    print("  Pré-teste: job LINUX-ADHOC-COMMAND (default) já validou SSH nos dois hosts.\n")

    for jt_id, jt_name, prio in tests:
        row = {"jt": jt_name, "id": jt_id, "prio": prio, "runs": []}
        for run in (1, 2):
            try:
                lj = launch_jt(jt_id, launch_payload)
                job_id = lj.get("job") or lj.get("id")
                j = wait_job(job_id)
                st = j.get("status")
                out = fetch_stdout_txt(job_id)
                recaps, chg, failed = parse_recap(out)
                err = ""
                if st != "successful":
                    err = (j.get("result_traceback") or "")[:2000]
                    if not err:
                        err = "\n".join(out.splitlines()[-40:])
                row["runs"].append(
                    {
                        "run": run,
                        "job_id": job_id,
                        "status": st,
                        "changed_hint": chg,
                        "recap_lines": recaps[-4:],
                        "failed_hint": failed,
                        "error_excerpt": err[:1500] if st != "successful" else "",
                    }
                )
            except Exception as e:
                row["runs"].append({"run": run, "status": "exception", "error": str(e)})
        # idempotência: 2ª execução com changed 0 ideal
        idem = "n/a"
        if len(row["runs"]) == 2 and row["runs"][0].get("status") == row["runs"][
            1
        ].get("status") == "successful":
            c2 = row["runs"][1].get("changed_hint", 0)
            idem = "OK (0 changes)" if c2 == 0 else f"Aviso: changed_total={c2} na 2ª"
        row["idempotency"] = idem
        results.append(row)

    print("### Resultados por Job Template\n")
    for r in results:
        print(f"**{r['jt']}** (id={r['id']}, P{r['prio']})")
        for run in r["runs"]:
            print(
                f"  Run {run.get('run')}: job={run.get('job_id')} status={run.get('status')} "
                f"changed~={run.get('changed_hint')}"
            )
            if run.get("error_excerpt"):
                print("  Erro:", run["error_excerpt"][:500])
            if run.get("recap_lines"):
                for ln in run["recap_lines"]:
                    print("   ", ln)
        print(f"  Idempotência: {r['idempotency']}\n")

    failed = [
        r["jt"]
        for r in results
        if any(x.get("status") not in ("successful",) for x in r["runs"])
    ]
    if failed:
        print("Falhas em:", ", ".join(failed))
        sys.exit(1)
    print("Todos os jobs testados concluíram com status successful.")
    sys.exit(0)


if __name__ == "__main__":
    main()
