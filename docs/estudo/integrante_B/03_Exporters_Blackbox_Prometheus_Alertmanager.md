# B3 — Exporters, Blackbox, Prometheus e Alertmanager (Integrante B)

Este módulo explica do zero a teoria por trás dos **Exporters**, da **Sonda Blackbox**, do **Prometheus (PromQL)** e do **Alertmanager por e-mail**, preparando você para a arguição.

> **Quer configurar seu Gmail, subir tudo e rodar os testes manuais P1, P2 e P3?** Siga o roteiro prático em [`docs/Guia_Execucao_e_Testes.md`](../../Guia_Execucao_e_Testes.md).

---

## 1. O que são Exporters? (E a diferença para o Agente do Zabbix)

Imagine que cada programa fala um idioma diferente:
- O **Linux** guarda dados de CPU/RAM em arquivos internos (`/proc`, `/sys`).
- O **PostgreSQL** guarda conexões e consultas em tabelas internas.
- O **Nginx** mostra conexões em texto simples no `/nginx_status`.

Nenhum deles entrega os dados no formato que o Prometheus entende (`/metrics`). Um **Exporter** é um "tradutor" leve que lê os números nativos do serviço e os traduz em métricas Prometheus (`nome_da_metrica{labels} valor`).

| Serviço / Alvo | Quem traduz | O que ele entrega (Requisito P1) |
| --- | --- | --- |
| **API FastAPI** | A própria API (`prometheus-client`) | `http_requests_total`, latência `p95`, pedidos, faturamento e pool do banco |
| **Nginx (`web`)** | `nginx-exporter` (`:9113`) | Lê `:8080/nginx_status` e expõe `nginx_connections_active`, `nginx_http_requests_total` |
| **PostgreSQL (`db`)** | `postgres-exporter` (`:9187`) | `pg_up` (1 = vivo, 0 = caiu), conexões ativas, transações e locks |
| **Host Linux** | `node-exporter` (`:9100`) | CPU, memória RAM (`node_memory_*`), disco e tráfego de rede do sistema |
| **Contêineres Docker** | `cadvisor` (`:8080` interno / `:8085` local) | CPU, RAM e rede isolados **por contêiner** (`api`, `web`, `db`, `prometheus`...) |

> **Diferença para o Zabbix (pergunta clássica da arguição!):**
> No Zabbix, um **único agente** (`zabbix-agent2`) instalado na máquina coleta tudo (CPU, Nginx, PostgreSQL via plugins). No mundo Prometheus, cada componente costuma ter um **exporter pequeno e especializado** (ou a própria aplicação já nasce com `/metrics`), e o Prometheus busca tudo via HTTP (*Pull*).

---

## 2. Monitoramento Whitebox vs. Blackbox (`sonda` na Filial)

- **Whitebox (caixa branca — olhando por dentro):** os exporters e `/metrics` mostram como os servidores estão por dentro (CPU, pool do banco, erros na API).
- **Blackbox (caixa preta — olhando por fora, como um cliente real):** na vida real, a API pode estar saudável na Matriz, mas um roteador quebrado impedir o cliente na Filial de comprar café!

Por isso colocamos o **Blackbox Exporter (`sonda`)** na **LAN Filial (`172.20.20.30`)** (Requisito P2). Quando o Prometheus quer testar um site, DNS ou ping **a partir da Filial**, ele pede para a `sonda`:
> *"Ei sonda (`:9115`), faça um teste `http_2xx` em `loja.cafeplanalto.lab` agora e me diga se deu certo (`probe_success = 1`) e quantos segundos demorou (`probe_duration_seconds`)!"*

### Os 3 módulos configurados em [`blackbox.yml`](../../../integrante_B/observability/blackbox/blackbox.yml)
1. **`http_2xx`:** faz `GET` em `/produtos` e `/health` esperando HTTP `200`.
2. **`dns_cafeplanalto`:** pergunta ao CoreDNS (`dns:53` / `172.20.10.10:53`) o IP de `loja.cafeplanalto.lab` e exige `NOERROR`.
3. **`icmp`:** envia `ping` para os roteadores (`10.0.0.1`, `10.0.0.2`) e servidores. *(Exige `cap_add: NET_RAW` no Docker para poder abrir pacotes ICMP.)*

### Como funciona o `relabel_configs` no `prometheus.yml`?
Você não precisa decorar, só entender a ideia: no job `blackbox_http`, colocamos em `targets` a URL da loja (`http://web/produtos`). O `relabel_configs` pega essa URL, guarda no parâmetro `?target=...` para a sonda testar, e troca o destino da requisição HTTP (`__address__`) para **`sonda:9115`** (no Containerlab, **`172.20.20.30:9115`**). Assim, **o Prometheus nunca acessa a loja direto — quem testa é sempre a sonda lá da Filial!**

---

## 3. Prometheus e PromQL do Zero

### 3.1 Ciclo Pull e Retenção de Memória (`7d`)
Em [`prometheus.local.yml`](../../../integrante_B/observability/prometheus/prometheus.local.yml) (para testes no Compose) e [`prometheus.clab.yml`](../../../integrante_B/observability/prometheus/prometheus.clab.yml) (para Containerlab 100% na rede `172.20.x.x`, sem nunca tocar em `172.30.0.x`):
- A cada **`15s`** (`scrape_interval`), o Prometheus raspa todos os alvos e avalia as regras de alerta (`evaluation_interval`).
- No [`Dockerfile`](../../../integrante_B/observability/prometheus/Dockerfile), configuramos `--storage.tsdb.retention.time=7d` para não encher disco e RAM da máquina durante o laboratório (dica explícita do PDF oficial).

### 3.2 Cinco expressões PromQL essenciais (para ler e explicar ao vivo)

| Expressão PromQL | O que ela calcula em português |
| --- | --- |
| `up` | `1` se o Prometheus conseguiu falar com o alvo na última coleta; `0` se caiu ou a WAN rompeu. |
| `probe_success{job="blackbox_http"}` | `1` se a sonda na Filial conseguiu HTTP `200` na loja; `0` se falhou. |
| `sum(rate(http_requests_total[1m]))` | Quantas requisições por segundo (`req/s`) a API recebeu no último minuto. |
| `sum(rate(http_requests_total{status=~"5.."}[1m])) / clamp_min(sum(rate(http_requests_total[1m])), 0.001)` | Fração de erro `5xx` (ex.: `0.20` = 20% das requisições dando erro 500). O `clamp_min` evita divisão por zero quando não há tráfego. |
| `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{rota=~"/produtos\|/pedidos"}[1m])))` | Latência **p95** em segundos (95% dos clientes foram atendidos em até este tempo). Nossa meta (SLO) é abaixo de `0.3` (300 ms). |

---

## 4. Regras de Alerta (`alerts.yml`) e Alertmanager por E-mail

### 4.1 Sintoma vs. Causa e o papel do `for:`
No roteiro oficial, o professor diferencia:
- **Alertas de sintoma** (o que o cliente sente — ex.: `LojaIndisponivelHTTP`, `TaxaDeErros5xxAlta`, `LatenciaP95AcimaDoSLO`): avisam imediatamente que a experiência do usuário quebrou.
- **Alertas de causa** (o motivo técnico — ex.: `BancoPostgreSQLFora`, `DNSInternoFalhando`, `EnlaceWANOuSondaIndisponivel`): ajudam a encontrar onde mexer.
- **Para que serve o `for: 15s`?** Evita alarmes falsos por uma oscilação de 1 segundo. O alerta entra primeiro em estado **`PENDING`** e só vira **`FIRING`** (dispara notificação) se o problema continuar verdadeiro durante todo o tempo do `for:`.

### 4.2 Agrupamento, Inibição e Auto-resolução no Alertmanager
Em [`alertmanager.yml.tmpl`](../../../integrante_B/observability/alertmanager/alertmanager.yml.tmpl):
- **Agrupamento (`group_by`, `group_wait: 15s`):** se 3 alertas do mesmo serviço dispararem quase juntos, o Alertmanager espera 15s e junta tudo em um único e-mail em vez de inundar sua caixa de entrada.
- **Inibição (`inhibit_rules`):** se um alerta `critical` já está ativo em um serviço, suprime o `warning` do mesmo serviço; e se a sonda na Filial sumir (`EnlaceWANOuSondaIndisponivel`), suprime os alertas secundários das sondas (`blackbox_http`, `blackbox_dns`, `blackbox_icmp`) para não gerar cascata.
- **Auto-resolução (`send_resolved: true`):** quando você desliga a falha e o Prometheus volta a ver tudo normal, o Alertmanager envia automaticamente um e-mail com **`[RESOLVED]`** (Requisito P3!).

### 4.3 Segurança de credenciais (`entrypoint.sh` + `.env`)
Senhas SMTP nunca vão para o Git. O arquivo `integrante_B/.env` fica listado no `.gitignore` e o [`entrypoint.sh`](../../../integrante_B/observability/alertmanager/entrypoint.sh) usa `envsubst` listando explicitamente apenas as 6 variáveis SMTP para gerar `/tmp/alertmanager.yml` ao iniciar o contêiner, mantendo os templates Go `{{ ... }}` intactos.

*(O passo a passo para criar a Senha de App no Gmail e rodar os ensaios manuais P1, P2 e P3 está em [`docs/Guia_Execucao_e_Testes.md`](../../Guia_Execucao_e_Testes.md).)*

---

## 5. Simulado de Arguição (Perguntas e Respostas da Fase 2)

1. **Qual a diferença entre um Exporter no Prometheus e o Agente do Zabbix?**
   > O Agente do Zabbix é um único serviço instalado no servidor que coleta múltiplas métricas (SO, banco, web). No Prometheus, cada componente expõe suas métricas via HTTP em `/metrics` (ou através de um exporter dedicado como `postgres_exporter`, `nginx-exporter` e `node_exporter`), e o Prometheus busca por *Pull*.
2. **Para que serve o Blackbox Exporter (`sonda`) e por que ele fica na Filial (`172.20.20.30`)?**
   > Ele testa a aplicação "por fora" (HTTP, DNS e ICMP) do ponto de vista de um usuário remoto. Ficando na Filial, qualquer falha na WAN (`10.0.0.0/30`), no roteamento ou no DNS interno aparece imediatamente em `probe_success == 0`.
3. **Por que todas as regras em `alerts.yml` têm o campo `for:`?**
   > Para evitar falsos positivos causados por picos momentâneos. A condição precisa permanecer verdadeira durante todo o tempo do `for:` (`PENDING` → `FIRING`) antes de o Prometheus enviar o alerta para o Alertmanager.
4. **Qual a diferença entre `group_by` e `inhibit_rules` no Alertmanager?**
   > `group_by` agrupa vários alertas semelhantes em uma única notificação para não dar spam. `inhibit_rules` silencia alertas secundários (ex.: `warning` quando já existe `critical` no mesmo serviço, ou falhas das sondas HTTP/DNS/ICMP quando a própria sonda na Filial ficou inacessível).
5. **Por que `prometheus.clab.yml` não pode apontar para `172.30.0.x`?**
   > Porque `172.30.0.0/24` é a rede de gerência fora de banda (`eth0`). Se a coleta passasse por ela, uma queda do enlace WAN ficaria invisível.
