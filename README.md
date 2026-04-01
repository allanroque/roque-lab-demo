# Roque Lab Demo

Repositório de laboratório para automações com **Ansible** e **Ansible Automation Platform (AAP)**.

## Objetivo

Este repositório contém playbooks e automações utilizadas em cenários de lab, incluindo:

- Provisionamento e configuração de servidores Linux
- Cenários de **AIOps e Self-Healing** com AAP e Event-Driven Ansible (EDA)
- Integrações com ferramentas de monitoramento (Prometheus, Grafana, Alertmanager)
- Automações de rede, DNS, IPAM e ServiceNow

## Estrutura

```
playbooks/
  <dominio>/              # Ex: linux, servicenow, dns, provisioning
    <acao>.yml            # Ex: deploy_apache.yml, change_close.yml
    files/                # Arquivos estáticos
    templates/            # Templates Jinja2
    vars/                 # Variáveis específicas
roles/                    # Roles reutilizáveis
inventory/                # Inventários
group_vars/               # Variáveis por grupo
host_vars/                # Variáveis por host
ansible.cfg               # Configuração do Ansible
```

## Requisitos

- Ansible Core 2.15+
- Ansible Automation Platform 2.5+
- Collections instaladas no Execution Environment do AAP

## Autor

Allan Roque
