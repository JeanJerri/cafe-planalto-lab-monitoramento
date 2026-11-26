# Café Planalto — Aplicação 3 Camadas, Carga e Observabilidade (Integrante B)

Stack do Integrante B para a loja virtual **Café Planalto** com testes locais no **WSL2 / Docker** antes da integração final no Containerlab.

## Estrutura de pastas

- [`api/`](api): API REST em Python + FastAPI (catálogo, pedidos, `/health`, `/metrics` Prometheus, `/admin/caos`, logs JSON e pool PostgreSQL resiliente).
- [`web/`](web): Proxy reverso Nginx (`loja.cafeplanalto.lab`), página HTML da loja, logs JSON e endpoint `stub_status` (`:8080/nginx_status`).
- [`db/`](db): Banco PostgreSQL 16 (`postgres:16-alpine` + `iproute2`) com [`init.sql`](db/init.sql).
- [`loadgen/`](loadgen): Gerador de carga contínuo em `k6` (`5` a `20 req/s`, padrão `10 req/s`).
- [`observability/`](observability):
  - [`blackbox/`](observability/blackbox): Blackbox Exporter (`http_2xx`, `dns_cafeplanalto`, `icmp`) + `iproute2`.
  - [`prometheus/`](observability/prometheus): `prometheus.local.yml`, `prometheus.clab.yml` (100% na rede de dados `172.20.x.x`) e [`rules/alerts.yml`](observability/prometheus/rules/alerts.yml) com retenção `7d`.
  - [`alertmanager/`](observability/alertmanager): template SMTP (`alertmanager.yml.tmpl`) com agrupamento, `inhibit_rules` e envio por e-mail (`send_resolved: true`).
  - [`dns-dev/`](observability/dns-dev): CoreDNS auxiliar para validar a sonda DNS no Compose local.
  - [`tests/`](observability/tests): testes automatizados das configurações de observabilidade.
- [`docker-compose.yml`](docker-compose.yml): Ambiente local completo das Fases 1 e 2.

## Como configurar o e-mail (Gmail + Senha de App) e subir tudo

> **Dica para WSL2:** mantenha o repositório no sistema de arquivos nativo Linux (`~/...`, não em `/mnt/c/...`).

1. Copie `.env.example` para `.env` (o `.env` fica ignorado no Git):
   ```bash
   cd integrante_B
   cp .env.example .env
   ```
2. Preencha as variáveis SMTP no `.env` (no Gmail, ative a verificação em 2 etapas e gere uma **Senha de App** de 16 caracteres sem espaços):
   ```env
   SMTP_SMARTHOST=smtp.gmail.com:587
   SMTP_FROM=seu.email@gmail.com
   SMTP_AUTH_USERNAME=seu.email@gmail.com
   SMTP_AUTH_PASSWORD=sua_senha_de_app_16_chars
   SMTP_REQUIRE_TLS=true
   ALERT_EMAIL_TO=seu.email@gmail.com
   ```
3. Suba toda a stack local:
   ```bash
   docker compose up -d --build
   ```

Portas locais (`127.0.0.1`, sem conflito com a porta `8080` do Zabbix):

| Serviço | URL Local |
| --- | --- |
| **Loja (Nginx)** | `http://localhost:8088` |
| **Status Nginx (`stub_status`)** | `http://localhost:8089/nginx_status` |
| **API / Swagger / Metrics** | `http://localhost:8000/docs` e `http://localhost:8000/metrics` |
| **Prometheus (Targets & Alerts)** | `http://localhost:9090` |
| **Alertmanager** | `http://localhost:9093` |
| **Blackbox Exporter (`sonda`)** | `http://localhost:9115` |
| **cAdvisor** | `http://localhost:8085` |

## Validações rápidas de CLI e Testes Automatizados

```bash
# Validar sintaxe de configuração e regras dentro dos contêineres:
docker exec cafeplanalto-dev-prometheus promtool check config /etc/prometheus/prometheus.yml
docker exec cafeplanalto-dev-prometheus promtool check rules /etc/prometheus/rules/alerts.yml
docker exec cafeplanalto-dev-alertmanager amtool check-config /tmp/alertmanager.yml

# Rodar todos os testes automatizados (API + configurações de observabilidade):
pytest -v api/tests observability/tests
```

Consulte o roteiro completo passo a passo (configuração do Gmail, testes manuais e checklist de apresentação) em [`../docs/Guia_Execucao_e_Testes.md`](../docs/Guia_Execucao_e_Testes.md) e os guias teóricos em [`../docs/estudo/README.md`](../docs/estudo/README.md).
