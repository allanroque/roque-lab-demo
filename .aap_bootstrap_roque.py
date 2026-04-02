#!/usr/bin/env python3
"""Bootstrap AAP resources for org ROQUE — run once; delete after use."""
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
EE_ID = 4  # Default execution environment (ee-supported-rhel9)

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


# Playbook path (under repo root) -> (JT name, cred: ssh|snow, label name)
PLAYBOOKS = [
    ("playbooks/dns/add_record.yml", "DNS-ADD-RECORD", "ssh", "dns"),
    ("playbooks/dns/del_record.yml", "DNS-DEL-RECORD", "ssh", "dns"),
    ("playbooks/dns/resolv_record.yml", "DNS-RESOLV-RECORD", "ssh", "dns"),
    ("playbooks/ipam/add_ip.yml", "IPAM-ADD-IP", "ssh", "ipam"),
    ("playbooks/ipam/del_ip.yml", "IPAM-DEL-IP", "ssh", "ipam"),
    ("playbooks/ipam/get_next_ip.yml", "IPAM-GET-NEXT-IP", "ssh", "ipam"),
    ("playbooks/provisioning/provision_vm.yml", "PROVISION-VM-LOCAL", "none", "provisioning"),
    ("playbooks/provisioning/destroy_vm.yml", "DESTROY-VM-LOCAL", "ssh_vmware", "provisioning"),
    ("playbooks/linux/adhoc/adhoc_checklist.yml", "LINUX-ADHOC-CHECKLIST", "ssh", "linux"),
    ("playbooks/linux/adhoc/adhoc_command.yml", "LINUX-ADHOC-COMMAND", "ssh", "linux"),
    ("playbooks/linux/adhoc/adhoc_logcollector.yml", "LINUX-ADHOC-LOGCOLLECTOR", "ssh", "linux"),
    ("playbooks/linux/adhoc/adhoc_services_linux.yml", "LINUX-ADHOC-SERVICES", "ssh", "linux"),
    ("playbooks/linux/adhoc/coringa.yml", "LINUX-ADHOC-CORINGA", "ssh", "linux"),
    ("playbooks/linux/apache/deploy_apache_rhel.yml", "APACHE-DEPLOY-LINUX-V1", "ssh", "linux"),
    ("playbooks/linux/chrony/config_chrony.yml", "LINUX-CONFIG-CHRONY", "ssh", "linux"),
    ("playbooks/linux/database/create_db_user.yml", "POSTGRES-CREATE-USER", "ssh", "linux"),
    ("playbooks/linux/database/health_check.yml", "POSTGRES-HEALTH-CHECK", "ssh", "linux"),
    ("playbooks/linux/dns/conf_linux_dns.yml", "LINUX-CONFIG-DNS", "ssh", "linux"),
    ("playbooks/linux/hardening/config-chrony.yml", "LINUX-HARDENING-CHRONY", "ssh", "linux"),
    ("playbooks/linux/hardening/config_agent_virt.yml", "LINUX-CONFIG-AGENT-VIRT", "ssh", "linux"),
    ("playbooks/linux/hardening/config_vmtools.yml", "LINUX-CONFIG-VMTOOLS", "ssh", "linux"),
    ("playbooks/linux/hardening/config_ansible_log.yml", "LINUX-HARDENING-ANSIBLE-LOG", "ssh", "linux"),
    ("playbooks/linux/hardening/config_basic_packages.yml", "LINUX-HARDENING-BASIC-PACKAGES", "ssh", "linux"),
    ("playbooks/linux/hardening/config_basic_services.yml", "LINUX-HARDENING-BASIC-SERVICES", "ssh", "linux"),
    ("playbooks/linux/hardening/config_cockpit.yml", "LINUX-CONFIG-COCKPIT", "ssh", "linux"),
    ("playbooks/linux/hardening/config_hardening_linux.yml", "LINUX-HARDENING", "ssh", "linux"),
    ("playbooks/linux/hardening/config_kernel_parameters.yml", "LINUX-CONFIG-KERNEL-PARAMS", "ssh", "linux"),
    ("playbooks/linux/hardening/config_motd.yml", "LINUX-HARDENING-MOTD", "ssh", "linux"),
    ("playbooks/linux/hardening/config_node_exporter.yml", "LINUX-CONFIG-NODE-EXPORTER", "ssh", "linux"),
    ("playbooks/linux/hardening/config_redhat_insights.yml", "LINUX-CONFIG-INSIGHTS", "ssh", "linux"),
    ("playbooks/linux/hardening/config_selinux.yml", "LINUX-HARDENING-SELINUX", "ssh", "linux"),
    ("playbooks/linux/hardening/config_service_users.yml", "LINUX-CONFIG-SERVICE-USERS", "ssh", "linux"),
    ("playbooks/linux/hardening/env_ansible.yml", "LINUX-ENV-ANSIBLE", "ssh", "linux"),
    ("playbooks/linux/hardening/promtail_agent.yml", "LINUX-CONFIG-PROMTAIL", "ssh", "linux"),
    ("playbooks/linux/logs/config_ansible_log.yml", "LINUX-CONFIG-ANSIBLE-LOG", "ssh", "linux"),
    ("playbooks/linux/motd/config_motd.yml", "LINUX-CONFIG-MOTD", "ssh", "linux"),
    ("playbooks/linux/nginx/deploy_nginx_rhel.yml", "NGINX-DEPLOY-LINUX", "ssh", "linux"),
    ("playbooks/linux/packages/config_packages_linux.yml", "LINUX-CONFIG-PACKAGES", "ssh", "linux"),
    ("playbooks/linux/selinux/config_selinux.yml", "LINUX-CONFIG-SELINUX", "ssh", "linux"),
    ("playbooks/linux/services/config_services_linux.yml", "LINUX-CONFIG-SERVICES", "ssh", "linux"),
    ("playbooks/linux/site-role-exec.yml", "LINUX-SITE-ROLE-EXEC", "ssh", "linux"),
    ("playbooks/linux/tools/tshoot_linux.yml", "LINUX-TSHOOT", "ssh", "linux"),
    ("playbooks/remediation/chatops-notify.yml", "REMEDIATION-CHATOPS-NOTIFY", "ssh", "remediation"),
    ("playbooks/remediation/investigate-host-health.yml", "REMEDIATION-INVESTIGATE-HOST", "ssh", "remediation"),
    ("playbooks/remediation/remediate-disk-cleanup.yml", "REMEDIATION-DISK-CLEANUP", "ssh", "remediation"),
    ("playbooks/remediation/remediate-high-cpu.yml", "REMEDIATION-HIGH-CPU", "ssh", "remediation"),
    ("playbooks/remediation/remediate-high-memory.yml", "REMEDIATION-HIGH-MEMORY", "ssh", "remediation"),
    ("playbooks/remediation/remediate-network.yml", "REMEDIATION-NETWORK", "ssh", "remediation"),
    ("playbooks/remediation/remediate-selinux.yml", "REMEDIATION-SELINUX", "ssh", "remediation"),
    ("playbooks/remediation/remediate-service-restart.yml", "REMEDIATION-SERVICE", "ssh", "remediation"),
    ("playbooks/self-healing/sh_disk_usage.yml", "SELF-HEALING-DISK-USAGE", "ssh", "remediation"),
    ("playbooks/servicenow/change_close.yml", "SNOW-CHANGE-CLOSE", "snow", "servicenow"),
    ("playbooks/servicenow/change_create.yml", "SNOW-CHANGE-CREATE", "snow", "servicenow"),
    ("playbooks/servicenow/incident_close.yml", "SNOW-INCIDENT-CLOSE", "snow", "servicenow"),
    ("playbooks/servicenow/incident_create.yml", "SNOW-INCIDENT-CREATE", "snow", "servicenow"),
]


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
            print(f"Project {project_id} SCM sync OK")
            return
        if st == "failed":
            raise SystemExit(f"Falha no sync do projeto {project_id}")
        time.sleep(3)
    raise SystemExit("Timeout aguardando sync do projeto")


def find_or_create_project():
    r = api("GET", f"/projects/?organization={ORG_ID}&search=PROJ-GIT-ROQUE-LAB")
    if r["count"]:
        p = r["results"][0]
        print(f"Project exists: {p['name']} id={p['id']}")
        return p["id"]
    body = {
        "name": "PROJ-GIT-ROQUE-LAB",
        "description": "Repositório roque-lab-demo — automações ROQUE",
        "organization": ORG_ID,
        "scm_type": "git",
        "scm_url": "https://github.com/allanroque/roque-lab-demo.git",
        "scm_branch": "main",
        "scm_clean": True,
        "scm_update_on_launch": True,
        "default_environment": EE_ID,
    }
    p = api("POST", "/projects/", body)
    print(f"Created project id={p['id']}")
    wait_project_sync(p["id"])
    return p["id"]


def find_or_create_credentials():
    r = api("GET", f"/credentials/?organization={ORG_ID}&search=CRED-SSH-LINUX-ROQUE")
    if r["count"]:
        ssh_id = r["results"][0]["id"]
        print(f"SSH cred exists id={ssh_id}")
    else:
        pwd = os.environ.get("ROQUE_SSH_PASSWORD")
        bpwd = os.environ.get("ROQUE_SSH_BECOME_PASSWORD", pwd)
        if not pwd:
            raise SystemExit(
                "Crie ROQUE_SSH_PASSWORD no ambiente para criar CRED-SSH-LINUX-ROQUE."
            )
        p = api(
            "POST",
            "/credentials/",
            {
                "name": "CRED-SSH-LINUX-ROQUE",
                "description": "SSH Linux lab ROQUE",
                "organization": ORG_ID,
                "credential_type": 1,
                "inputs": {
                    "username": os.environ.get("ROQUE_SSH_USER", "ansible"),
                    "password": pwd,
                    "become_method": "sudo",
                    "become_username": "root",
                    "become_password": bpwd,
                },
            },
        )
        ssh_id = p["id"]
        print(f"Created SSH cred id={ssh_id}")

    r = api("GET", f"/credentials/?organization={ORG_ID}&search=CRED-SNOW-ROQUE")
    if r["count"]:
        snow_id = r["results"][0]["id"]
        print(f"SNOW cred exists id={snow_id}")
    else:
        su = os.environ.get("ROQUE_SNOW_USERNAME")
        si = os.environ.get("ROQUE_SNOW_INSTANCE")
        sp = os.environ.get("ROQUE_SNOW_PASSWORD")
        if not all([su, si, sp]):
            raise SystemExit(
                "Defina ROQUE_SNOW_USERNAME, ROQUE_SNOW_INSTANCE, ROQUE_SNOW_PASSWORD "
                "para criar CRED-SNOW-ROQUE."
            )
        p = api(
            "POST",
            "/credentials/",
            {
                "name": "CRED-SNOW-ROQUE",
                "description": "ServiceNow ROQUE",
                "organization": ORG_ID,
                "credential_type": 31,
                "inputs": {
                    "SNOW_USERNAME": su,
                    "SNOW_INSTANCE": si,
                    "SNOW_PASSWORD": sp,
                },
            },
        )
        snow_id = p["id"]
        print(f"Created SNOW cred id={snow_id}")
    return ssh_id, snow_id


def find_or_create_inventory():
    r = api("GET", f"/inventories/?organization={ORG_ID}&search=INV-ROQUE-LAB")
    if r["count"]:
        inv = r["results"][0]["id"]
        print(f"Inventory exists id={inv}")
    else:
        p = api(
            "POST",
            "/inventories/",
            {
                "name": "INV-ROQUE-LAB",
                "description": "Inventário lab ROQUE",
                "organization": ORG_ID,
            },
        )
        inv = p["id"]
        print(f"Created inventory id={inv}")

    hosts = ["server01.aroque.com.br", "server02.aroque.com.br"]
    host_ids = []
    for h in hosts:
        r = api("GET", f"/hosts/?inventory={inv}&name={h}")
        if r["count"]:
            hid = r["results"][0]["id"]
        else:
            p = api(
                "POST",
                "/hosts/",
                {"name": h, "inventory": inv, "enabled": True},
            )
            hid = p["id"]
            print(f"Created host {h} id={hid}")
        host_ids.append(hid)

    r = api("GET", f"/groups/?inventory={inv}&name=lab_servers")
    if r["count"]:
        gid = r["results"][0]["id"]
        print(f"Group lab_servers exists id={gid}")
    else:
        p = api(
            "POST",
            "/groups/",
            {"name": "lab_servers", "inventory": inv},
        )
        gid = p["id"]
        print(f"Created group id={gid}")

    for gname in ("infra", "nginx", "apache", "postgresql", "infra-3-tier"):
        r = api("GET", f"/groups/?inventory={inv}&name={gname}")
        if r["count"]:
            print(f"Group {gname} exists id={r['results'][0]['id']}")
        else:
            p = api("POST", "/groups/", {"name": gname, "inventory": inv})
            print(f"Created group {gname} id={p['id']}")

    for hid in host_ids:
        try:
            api("POST", f"/groups/{gid}/hosts/", {"id": hid})
        except urllib.error.HTTPError as e:
            if e.code not in (400, 204):
                raise
    return inv


def ensure_labels():
    names = [
        "linux",
        "servicenow",
        "dns",
        "ipam",
        "remediation",
        "config",
        "deploy",
        "database",
        "aws",
        "cloud",
        "provisioning",
    ]
    label_map = {}
    for name in names:
        r = api("GET", f"/labels/?organization={ORG_ID}&name={name}")
        if r["count"]:
            label_map[name] = r["results"][0]["id"]
        else:
            p = api("POST", "/labels/", {"name": name, "organization": ORG_ID})
            label_map[name] = p["id"]
            print(f"Created label {name} id={p['id']}")
    return label_map


def all_labels_for_jt(jt_name: str, primary: str) -> list[str]:
    """Labels por JT: domínio (linux/dns/…) + config / deploy / database conforme o caso."""
    labs = [primary]
    if jt_name in ("APACHE-DEPLOY-LINUX-V1", "NGINX-DEPLOY-LINUX"):
        labs.append("deploy")
        return labs
    if jt_name in ("POSTGRES-CREATE-USER", "POSTGRES-HEALTH-CHECK"):
        labs.append("database")
        return labs
    if primary == "servicenow":
        return labs
    if primary == "remediation":
        return labs
    if primary in ("dns", "ipam"):
        labs.append("config")
        return labs
    if primary == "provisioning":
        labs.append("config")
        return labs
    if primary == "linux":
        if jt_name.startswith("LINUX-ADHOC") or jt_name == "LINUX-TSHOOT":
            return labs
        labs.append("config")
        return labs
    return labs


def jt_exists(project_id, name):
    r = api("GET", f"/job_templates/?project={project_id}&name={name}")
    return r["results"][0]["id"] if r["count"] else None


def default_limit_for_jt(name: str) -> str:
    """Padrão de limit (grupo do inventário); vazio para API/localhost (AWS, SNOW, DNS, IPAM)."""
    if name.startswith("AWS-") or name == "AWS-UPDATE-AAP-CREDENTIALS":
        return ""
    if name.startswith("SNOW-"):
        return ""
    if name.startswith("DNS-") or name.startswith("IPAM-"):
        return ""
    if name.startswith("PROVISION-") or name.startswith("DESTROY-"):
        return ""
    if name in ("APACHE-DEPLOY-LINUX", "APACHE-DEPLOY-LINUX-V1"):
        return "apache"
    if name in ("NGINX-DEPLOY-LINUX", "DEPLOY-NGINX-LINUX"):
        return "nginx"
    if name in ("POSTGRES-CREATE-USER", "POSTGRES-HEALTH-CHECK", "POSTGRES-DEPLOY-LINUX"):
        return "postgresql"
    if name in ("DEPLOY-APP-LINUX", "DEPLOY-NODEJS-LINUX"):
        return "app"
    return "infra"


def associate_cred(jt_id, cred_id):
    try:
        api("POST", f"/job_templates/{jt_id}/credentials/", {"id": cred_id})
    except urllib.error.HTTPError as e:
        if e.code in (400, 204):
            return
        raise


def associate_label(jt_id, label_id):
    try:
        api("POST", f"/job_templates/{jt_id}/labels/", {"id": label_id})
    except urllib.error.HTTPError:
        pass


def credential_id_by_name(name: str):
    """Credencial na org ROQUE pelo nome exato (ex.: CRED-VMWARE-ROQUE)."""
    r = api("GET", f"/credentials/?organization={ORG_ID}&name={name}")
    return r["results"][0]["id"] if r["count"] else None


def create_job_templates(project_id, inventory_id, ssh_id, snow_id, label_map):
    jt_by_name = {}
    for playbook, name, cred_kind, lab in PLAYBOOKS:
        if cred_kind == "ssh":
            cred_id = ssh_id
            become = True
        elif cred_kind == "snow":
            cred_id = snow_id
            become = False
        elif cred_kind == "ssh_vmware":
            cred_id = None
            become = False
        else:
            cred_id = None
            become = False
        existing = jt_exists(project_id, name)
        body = {
            "name": name,
            "description": "",
            "job_type": "run",
            "inventory": inventory_id,
            "project": project_id,
            "playbook": playbook,
            "verbosity": 1,
            "execution_environment": EE_ID,
            "become_enabled": become,
            "diff_mode": True,
            "limit": default_limit_for_jt(name),
        }
        if existing:
            p = api("PATCH", f"/job_templates/{existing}/", body)
            jtid = existing
            print(f"Updated JT {name} id={jtid}")
        else:
            p = api("POST", "/job_templates/", body)
            jtid = p["id"]
            print(f"Created JT {name} id={jtid}")
        if cred_kind == "ssh_vmware":
            if ssh_id is not None:
                associate_cred(jtid, ssh_id)
            vmw = credential_id_by_name("CRED-VMWARE-ROQUE")
            if vmw is not None:
                associate_cred(jtid, vmw)
            else:
                print(f"WARN: CRED-VMWARE-ROQUE não encontrada — associe manualmente ao JT {name}")
        elif cred_id is not None:
            associate_cred(jtid, cred_id)
        for lbl in all_labels_for_jt(name, lab):
            associate_label(jtid, label_map[lbl])
        jt_by_name[name] = jtid
    return jt_by_name


def wf_exists(name):
    r = api("GET", f"/workflow_job_templates/?organization={ORG_ID}&name={name}")
    return r["results"][0]["id"] if r["count"] else None


def create_workflow(name, jt_by_name, chain):
    """chain: list of JT names in order."""
    wfid = wf_exists(name)
    if wfid:
        print(f"Workflow {name} exists id={wfid} — skipping node rebuild")
        return wfid
    wf = api(
        "POST",
        "/workflow_job_templates/",
        {"name": name, "description": "", "organization": ORG_ID},
    )
    wfid = wf["id"]
    print(f"Created workflow {name} id={wfid}")

    nodes = []
    for jtname in chain:
        jid = jt_by_name[jtname]
        n = api(
            "POST",
            "/workflow_job_template_nodes/",
            {
                "workflow_job_template": wfid,
                "unified_job_template": jid,
            },
        )
        nodes.append(n["id"])
    # Encadear via POST /success_nodes/ (PATCH com lista de ids não aplica nesta API)
    for i in range(len(nodes) - 1):
        api(
            "POST",
            f"/workflow_job_template_nodes/{nodes[i]}/success_nodes/",
            {"id": nodes[i + 1]},
        )
    return wfid


def sync_labels_only():
    """Atualiza labels em todos os JTs do projeto ROQUE (idempotente)."""
    if not TOKEN:
        print("Set AAP_ADMIN_TOKEN", file=sys.stderr)
        sys.exit(1)
    r = api("GET", f"/projects/?organization={ORG_ID}&search=PROJ-GIT-ROQUE-LAB")
    if not r["count"]:
        raise SystemExit("Projeto PROJ-GIT-ROQUE-LAB não encontrado.")
    pid = r["results"][0]["id"]
    label_map = ensure_labels()
    for playbook, name, cred_kind, lab in PLAYBOOKS:
        jtid = jt_exists(pid, name)
        if not jtid:
            print(f"Skip (JT inexistente): {name}")
            continue
        for lbl in all_labels_for_jt(name, lab):
            associate_label(jtid, label_map[lbl])
        print(f"Labels OK: {name} (id={jtid}) -> {all_labels_for_jt(name, lab)}")
    print("Sincronização de labels concluída.")


def main():
    if not TOKEN:
        print("Set AAP_ADMIN_TOKEN", file=sys.stderr)
        sys.exit(1)
    print("--- Project ---")
    pid = find_or_create_project()
    print("--- Credentials ---")
    ssh_id, snow_id = find_or_create_credentials()
    print("--- Inventory ---")
    inv = find_or_create_inventory()
    print("--- Labels ---")
    label_map = ensure_labels()
    print("--- Job templates ---")
    jt_by_name = create_job_templates(pid, inv, ssh_id, snow_id, label_map)
    print("--- Workflows ---")
    create_workflow(
        "WF-REMEDIATION-SERVICE",
        jt_by_name,
        ["SNOW-INCIDENT-CREATE", "REMEDIATION-SERVICE", "SNOW-INCIDENT-CLOSE"],
    )
    create_workflow(
        "WF-LINUX-FULL-SETUP",
        jt_by_name,
        ["LINUX-HARDENING", "LINUX-CONFIG-PACKAGES", "LINUX-CONFIG-CHRONY", "LINUX-CONFIG-MOTD"],
    )
    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sync-labels-only":
        sync_labels_only()
    else:
        main()
