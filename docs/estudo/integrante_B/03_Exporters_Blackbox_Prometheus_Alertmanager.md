# B3 — Exporters, Sonda Blackbox, Prometheus e Alertmanager (Do Zero)

Neste módulo você entende a lógica completa da pilha de coleta e alertas do **Integrante B**: quem mede os números, quem testa a loja de longe, quem guarda tudo e quem manda o e-mail para o seu celular.

> **Para subir tudo e rodar os comandos completos no WSL2**, use o manual separado: [`docs/Guia_Execucao_e_Testes.md`](../../Guia_Execucao_e_Testes.md).

---

## 1. Exporters — Os "Tradutores" de Métricas

### 1) Por que isso existe?
O PostgreSQL guarda quantas consultas estão rodando, o Nginx conta conexões abertas e o Linux sabe quanta RAM está livre — mas cada um fala uma língua diferente. O Prometheus só entende **uma única língua**: texto no padrão `/metrics`.
Um **Exporter** é um programa pequeno que lê os dados internos de um serviço e traduz para `/metrics`.

### 2) Onde está no projeto (`integrante_B/docker-compose.yml`)?
| Serviço | Quem traduz | O que entrega |
| --- | --- | --- |
| **`api`** | A própria API (`prometheus-client`) | Pedidos, faturamento, erros HTTP, latência `p95`, pool |
| **`web` (Nginx)** | `nginx-exporter` (`:9113`) | Lê `:8080/nginx_status` e expõe conexões e requisições |
| **`db` (PostgreSQL)** | `postgres-exporter` (`:9187`) | `pg_up` (`1` = vivo, `0` = caiu), transações e conexões |
| **Máquina Linux** | `node-exporter` (`:9100`) | CPU, memória RAM (`node_memory_*`), disco e rede do host |
| **Contêineres** | `cadvisor` (`:8085` local) | CPU e RAM isolados **de cada contêiner** (`api`, `web`, `db`...) |

> **Diferença para o Zabbix:** no Zabbix, um único agente (`zabbix-agent2`) instalado no servidor coleta tudo. No Prometheus, cada componente tem seu exporter especializado (ou já nasce expondo `/metrics`).

### 3) Valide em 10 segundos
Abra **`http://127.0.0.1:9090/targets`**: cada linha verde **`UP`** significa que o Prometheus conseguiu conversar com aquele exporter nos últimos 15 segundos!

---

## 2. Whitebox vs. Blackbox — A Sonda na Filial (`sonda`)

### 1) Por que isso existe?
Olhar CPU, memória e banco (**Whitebox**, por dentro) não garante que o cliente consiga comprar. O servidor na Matriz pode estar perfeito, mas um cabo cortado ou DNS quebrado impede o cliente na Filial de abrir o site!
Por isso colocamos o **Blackbox Exporter (`sonda`)** lá na **Filial (`172.20.20.30`)**: ele testa a loja **por fora**, exatamente como um cliente remoto atravessando a WAN.

### 2) Como funciona? (3 testes configurados em [`blackbox.yml`](../../../integrante_B/observability/blackbox/blackbox.yml))
1. **`http_2xx`:** tenta abrir `/produtos` e `/health` esperando HTTP `200`.
2. **`dns_cafeplanalto`:** pergunta ao DNS interno (`dns:53` / `172.20.10.10:53`) qual o IP de `loja.cafeplanalto.lab`.
3. **`icmp`:** dispara `ping` para roteadores e servidores.

*E como o Prometheus manda a sonda fazer o teste?* Pelo bloco `relabel_configs` em `prometheus.*.yml`: o Prometheus envia a URL da loja como parâmetro (`?target=http://web/produtos`) para o endereço da `sonda:9115` (`172.20.20.30:9115` no Containerlab). A sonda devolve duas métricas principais: **`probe_success`** (`1` = passou, `0` = falhou) e **`probe_duration_seconds`** (tempo gasto).

### 3) Valide em 10 segundos + "E se eu parar o DNS?"
1. Abra **`http://127.0.0.1:9090/graph`**, mude para **Table** e consulte `probe_success`: todos devem valer **`1`**.
2. Se rodar `docker stop cafeplanalto-dev-dns`, em ~15s o `probe_success{job="blackbox_dns"}` cai para **`0`**.

---

## 3. Prometheus: Coleta *Pull*, Retenção `7d` e PromQL sem Mistério

### 1) Por que o Prometheus "puxa" os dados (*Pull*) em vez de receber (*Push*)?
- **No Pull (usado pelo Prometheus):** o servidor de monitoramento bate na porta de cada alvo a cada 15 segundos (`scrape_interval: 15s`).
- **Grande vantagem:** a API não precisa saber onde o Prometheus mora. E se a API morrer ou a WAN cair, o Prometheus percebe na hora que não conseguiu buscar `/metrics` e marca **`up == 0`**.
- **Por que configuramos `--storage.tsdb.retention.time=7d` no [`Dockerfile`](../../../integrante_B/observability/prometheus/Dockerfile)?** Para apagar dados com mais de 7 dias e impedir o Prometheus de consumir toda a RAM da máquina.
- **Por que existem dois arquivos (`prometheus.local.yml` e `prometheus.clab.yml`)?** O `.local.yml` usa os nomes do Docker Compose para testarmos rápido no WSL2; o `.clab.yml` usa **apenas os IPs da rede de dados `172.20.x.x` e `10.0.0.x`** (jamais `172.30.0.x` da `eth0`!) para a integração final no Containerlab.

### 2) Lendo as 5 consultas PromQL essenciais (teste direto em `:9090/graph`)
* **`up`**: vale `1` se o alvo respondeu à coleta; `0` se caiu.
* **`probe_success{job="blackbox_http"}`**: vale `1` se a sonda HTTP na Filial obteve `200 OK`.
* **`sum(rate(http_requests_total[1m]))`**: transforma o contador acumulado em **requisições por segundo (`req/s`)** no último minuto.
* **`sum(rate(http_requests_total{status=~"5.."}[1m])) / clamp_min(sum(rate(http_requests_total[1m])), 0.001)`**: porcentagem de erro 500 (`0.2` = 20% falhando). O `clamp_min` só impede divisão por zero quando a loja está parada.
* **`histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{rota=~"/produtos\|/pedidos"}[1m])))`**: calcula a latência **`p95`** em segundos (nossa meta é `< 0.3` = 300 ms).

---

## 4. Regras de Alerta (`alerts.yml`) e Alertmanager por E-mail

### 1) Por que isso existe?
Não queremos ficar olhando gráficos 24 horas por dia. O **Prometheus** avalia as regras em [`rules/alerts.yml`](../../../integrante_B/observability/prometheus/rules/alerts.yml) a cada 15s; quando algo quebra, ele avisa o **Alertmanager** ([`alertmanager.yml.tmpl`](../../../integrante_B/observability/alertmanager/alertmanager.yml.tmpl)), que envia um e-mail para o seu celular.

### 2) Três regras de ouro dentro dos nossos alertas
1. **Sintoma vs. Causa:** separamos alertas do que o cliente sente (`TaxaDeErros5xxAlta`, `LatenciaP95AcimaDoSLO`, `LojaIndisponivelHTTP` → **sintoma**) dos alertas do motivo técnico (`BancoPostgreSQLFora`, `DNSInternoFalhando`, `EnlaceWANOuSondaIndisponivel` → **causa**).
2. **Para que serve `for: 15s`?** Evita alarme falso por uma piscada de 1 segundo. O alerta passa por 3 estágios em `:9090/alerts`:
   - `Inactive` (verde — tudo normal) → `Pending` (amarelo — deu erro, contando os 15s) → **`Firing`** (vermelho — durou mais que `for:`, dispara o e-mail!).
3. **Agrupamento (`group_by`) + Inibição (`inhibit_rules`) + Auto-resolução (`send_resolved: true`):**
   - `group_by` junta alertas parecidos em **um só e-mail** (sem spam).
   - `inhibit_rules` evita cascata: se um alerta `critical` dispara em um serviço, ele silencia o `warning` do mesmo serviço; se a `sonda` cair, silencia os alertas das sondas HTTP/DNS/ICMP.
   - `send_resolved: true`: quando você desliga a falha, o Alertmanager envia outro e-mail escrito **`[RESOLVED]`** sozinho!

### 3) Como sua senha do Gmail fica segura?
Senhas nunca vão para o Git. Você coloca no arquivo `integrante_B/.env` (ignorado pelo `.gitignore`), e o [`entrypoint.sh`](../../../integrante_B/observability/alertmanager/entrypoint.sh) injeta as 6 variáveis SMTP na hora que o contêiner liga.

### 4) Valide em 10 segundos
Na aba **"Laboratório de Caos & Raio-X HTTP"** de `http://127.0.0.1:8088`, clique no botão vermelho **"Falha 6: Erros 500 (20%)"**, acompanhe em `http://127.0.0.1:9090/alerts` o alerta `TaxaDeErros5xxAlta` ficar vermelho (**`Firing`**) e confirme o e-mail **`[FIRING]`** no celular. Depois clique em **"Normal (0ms / 0%)"** para receber o **`[RESOLVED]`**!

---

## 5. Simulado Rápido (Perguntas de Arguição)
1. **Pull vs. Push:** Prometheus usa *Pull* (`/metrics`); se o alvo cair ou a WAN romper, ele sabe na hora (`up == 0`).
2. **Exporter vs. Agente Zabbix:** Zabbix usa um agente geral por servidor; Prometheus usa exporters especializados por serviço.
3. **Por que Blackbox na Filial?** Porque mede o que o cliente remoto sente atravessando a WAN (`probe_success` HTTP/DNS/ICMP).
4. **Para que servem `for:` e `inhibit_rules`?** `for:` evita falsos positivos por picos curtos; `inhibit_rules` silencia alertas secundários em cascata quando a causa raiz já disparou.
