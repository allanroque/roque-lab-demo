# Ansible Automation Platform — Guia do Projeto

## Visão Geral
Repositório de automações Ansible para uso no Ansible Automation Platform (AAP).
Estratégia baseada em diretórios por domínio/serviço com playbooks simples.
Roles são usadas apenas quando a complexidade justifica.

## Comandos Úteis
- **Lint**: `ansible-lint`
- **Syntax check**: `ansible-playbook --syntax-check <playbook>.yml`
- **Dry-run**: `ansible-playbook -i inventory --check --diff <playbook>.yml`
- **Execução**: `ansible-playbook -i inventory <playbook>.yml`

## Estrutura de Diretórios
```
playbooks/
  <dominio>/              # Ex: servicenow, linux, dns, ipam, provisioning
    <acao>.yml            # Ex: change_close.yml, add_record.yml
    files/                # Arquivos estáticos (configs, scripts)
    templates/            # Templates Jinja2 (.j2)
    vars/                 # Variáveis específicas (se necessário)
roles/                    # Apenas quando a complexidade justifica
inventory/                # Inventários estáticos ou dinâmicos
group_vars/               # Variáveis por grupo
host_vars/                # Variáveis por host
ansible.cfg               # Configuração do Ansible
```

## Nomenclatura
- Diretórios representam o domínio/serviço: `servicenow`, `dns`, `linux/hardening`
- Playbooks descrevem a ação: `change_close.yml`, `add_record.yml`, `deploy_apache_rhel.yml`
- No AAP o caminho completo identifica a automação: `playbooks/servicenow/change_close.yml`
- Variáveis devem ser pensadas para uso em **Surveys do AAP** (inputs do usuário)

## Padrão do ansible.cfg
- `gathering = smart` — coleta inteligente de facts
- `callbacks_enabled = timer, profile_tasks, profile_roles` — profiling ativo
- `diff_always = True` — sempre mostrar diffs
- `host_key_checking = false` — desabilitado para labs
- `pipelining = True` — otimização SSH
- `become = true`, `become_method = sudo`, `become_user = root`

## Padrões de Código

### FQCN Obrigatório
Sempre usar o nome completo do módulo (Fully Qualified Collection Name):

| Módulo | FQCN |
|--------|------|
| yum | `ansible.builtin.yum` |
| dnf | `ansible.builtin.dnf` |
| apt | `ansible.builtin.apt` |
| copy | `ansible.builtin.copy` |
| template | `ansible.builtin.template` |
| file | `ansible.builtin.file` |
| service | `ansible.builtin.service` |
| systemd | `ansible.builtin.systemd` |
| user | `ansible.builtin.user` |
| group | `ansible.builtin.group` |
| lineinfile | `ansible.builtin.lineinfile` |
| blockinfile | `ansible.builtin.blockinfile` |
| command | `ansible.builtin.command` |
| debug | `ansible.builtin.debug` |
| set_fact | `ansible.builtin.set_fact` |
| assert | `ansible.builtin.assert` |
| uri | `ansible.builtin.uri` |
| package | `ansible.builtin.package` |
| cron | `ansible.builtin.cron` |
| firewalld | `ansible.posix.firewalld` |
| seboolean | `ansible.posix.seboolean` |
| selinux | `ansible.posix.selinux` |
| mount | `ansible.posix.mount` |
| nmcli | `community.general.nmcli` |
| timezone | `community.general.timezone` |
| mysql_db | `community.mysql.mysql_db` |
| mysql_user | `community.mysql.mysql_user` |
| postgresql_db | `community.postgresql.postgresql_db` |
| postgresql_user | `community.postgresql.postgresql_user` |
| snow_record | `servicenow.itsm.snow_record` |
| now | `servicenow.itsm.now` |
| ec2_instance | `amazon.aws.ec2_instance` |
| s3_bucket | `amazon.aws.s3_bucket` |

### Tasks
- Sempre incluir `name:` descritivo e claro em português ou inglês
- Usar `block:` para agrupar tasks relacionadas com tratamento de erro
- Usar `tags:` para execução seletiva
- Usar `when:` para condicionais claros
- Registrar resultados com `register:` quando necessário
- Incluir `changed_when:` e `failed_when:` para idempotência

### Variáveis
- Nomes descritivos em snake_case: `app_service_port`, `db_admin_user`
- Pensar nas variáveis como campos de **Survey no AAP**
- Definir defaults quando possível
- Documentar variáveis no topo do playbook ou em `vars/`

### Proibições
- **NÃO** usar módulos `ansible.builtin.shell` ou `ansible.builtin.raw` — preferir módulos específicos
- **NÃO** chamar shell scripts externos
- **NÃO** criar `requirements.yml` de collections no repositório (torna o sync do Project no AAP lento)
- **NÃO** hardcodar credenciais — usar credentials do AAP

### Quando Usar Role vs Diretório Simples
- **Diretório simples**: automação pequena, até ~100 linhas, escopo bem definido
- **Role**: lógica reutilizável, múltiplos playbooks consomem, handlers complexos, templates variados

## Validação
Antes de commitar, garantir:
1. `ansible-lint` sem erros
2. `ansible-playbook --syntax-check` OK
3. Variáveis documentadas e pensadas para Survey do AAP
4. FQCN em todos os módulos
5. Sem uso de shell/raw/scripts
