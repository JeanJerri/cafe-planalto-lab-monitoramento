# B1 — Aplicação em 3 Camadas: Nginx, API FastAPI e PostgreSQL (Integrante B)

Este guia explica do zero toda a arquitetura da **Loja Café Planalto** construída em [`integrante_B/`](../../integrante_B/): como as três camadas conversam, como a API mede métricas/logs e como ela resiste à queda do banco de dados.

---

## 1. Conceitos Básicos: HTTP, REST, JSON e Docker

### 1.1 Cliente, Servidor, IP e Porta
- **Cliente:** quem faz a requisição (navegador, `curl` ou gerador de carga `k6`).
- **Servidor:** programa que fica escutando uma **porta** dentro de um **IP** (ex.: `172.20.10.20:80` para o Nginx; `172.20.10.21:8000` para a API; `172.20.10.22:5432` para o PostgreSQL).

### 1.2 HTTP, API REST e JSON
O protocolo **HTTP** funciona por requisição e resposta:
- **Método:** `GET` (consultar/listar, ex.: `/produtos`, `/health`, `/metrics`) e `POST` (enviar dados para criar/executar, ex.: `/pedidos`, `/admin/caos`).
- **Status Code:**
  - `200 OK`: sucesso na leitura/operação.
  - `201 Created`: novo pedido gravado com sucesso.
  - `404 Not Found`: produto inexistente.
  - `500 Internal Server Error`: erro interno (simulado de propósito pelo `/admin/caos` na Falha 6).
  - `503 Service Unavailable`: a API está viva, mas o banco PostgreSQL atrás dela está fora do ar (Falha 4).
- **JSON:** formato de texto estruturado em pares `"chave": valor` (ex.: `{"produto_id": 1, "quantidade": 2}`).

### 1.3 Docker, `Dockerfile` e por que instalamos `iproute2`
- **VM vs. Contêiner:** uma VM virtualiza um computador inteiro (gasta GBs de RAM). Um contêiner Docker compartilha o kernel do Linux do hospedeiro, subindo em segundos com poucos MB.
- **`Dockerfile`:** receita de texto para montar uma imagem.
- **`iproute2`:** pacote instalado nos Dockerfiles de `web`, `api`, `db` e `loadgen`. Ele fornece o comando `ip` (`ip addr`, `ip route`), que o Containerlab executa dentro de cada contêiner ao montar as interfaces `eth1` e as rotas estáticas!

---

## 2. Arquitetura em 3 Camadas da Loja Café Planalto

```text
  Cliente / Filial (172.20.20.20)
         │  HTTP :80 (loja.cafeplanalto.lab)
         ▼
  [1] WEB — Nginx (172.20.10.20)
         │  • Serve a página HTML em "/"
         │  • Proxy reverso para /produtos, /pedidos, /health, /admin/caos
         │  • Gera X-Trace-Id e imprime access log em JSON
         │  • Porta :8080/nginx_status (stub_status para exporters/Zabbix)
         ▼  HTTP :8000
  [2] API — Python + FastAPI + Uvicorn (172.20.10.21)
         │  • Regras da loja + middleware de métricas, logs JSON e caos
         │  • Pool de conexões (psycopg_pool) com retry e reconexão automática
         ▼  TCP :5432
  [3] DB — PostgreSQL 16 (172.20.10.22)
            • Tabelas "produtos" (5 cafés) e "pedidos"
```

### Camada 1: `web` — Nginx ([`integrante_B/web/`](../../integrante_B/web/))
- **Por que usar um Proxy Reverso?** O usuário acessa um endereço único padrão na porta `80` (`http://loja.cafeplanalto.lab`). O Nginx entrega a página estática [`index.html`](../../integrante_B/web/html/index.html) em `/` e encaminha chamadas de API (`/produtos`, `/pedidos`, `/health`, `/admin/caos`) para a API Python na porta `8000`.
- **Correlação (`X-Trace-Id`):** em [`nginx.conf`](../../integrante_B/web/nginx.conf), se o cliente não enviar `X-Trace-Id`, o Nginx cria um ID único (`$request_id`), envia para a API e grava nos dois logs (Nginx e API).
- **`NGINX_ENVSUBST_FILTER="^API_UPSTREAM$"`:** no [`Dockerfile`](../../integrante_B/web/Dockerfile), restringimos a substituição de variáveis de ambiente apenas a `${API_UPSTREAM}`, evitando que o entrypoint oficial do Nginx apague variáveis internas como `$uri`, `$status` e `$request_id`.
- **`stub_status` (porta `8080/nginx_status`):** página interna com contadores de conexões ativas e requisições atendidas, usada pelo `nginx-prometheus-exporter` (Integrante B) e pelo template Nginx do Zabbix (Integrante A).

### Camada 2: `api` — FastAPI ([`integrante_B/api/`](../../integrante_B/api/))
- **FastAPI + Pydantic + Uvicorn:** `FastAPI` define as rotas, `Pydantic` ([`models.py`](../../integrante_B/api/src/models.py)) valida entradas inválidas (ex.: `quantidade <= 0` ou `taxa_erro > 1.0`) e `Uvicorn` é o servidor web assíncrono (`async/await`) que atende múltiplos clientes sem travar durante atrasos de caos.
- **Middleware (`observability_and_chaos_middleware` em [`main.py`](../../integrante_B/api/src/main.py)):** funciona como uma catraca única que, em toda requisição:
  1. Inicia o cronômetro e extrai `trace_id` (`traceparent` ou `X-Trace-Id`).
  2. Se a rota não for isenta, aplica atraso (`await asyncio.sleep`) ou sorteia erro HTTP `500` conforme `/admin/caos`.
  3. Executa a rota (capturando `DatabaseUnavailableError` como HTTP `503`).
  4. Atualiza as métricas Prometheus e imprime 1 linha de **log JSON no `stdout`** (com `PYTHONUNBUFFERED=1` e `--no-access-log` para não misturar texto puro).

### Camada 3: `db` — PostgreSQL ([`integrante_B/db/`](../../integrante_B/db/))
- O [`init.sql`](../../integrante_B/db/init.sql) cria as tabelas `produtos` e `pedidos` e insere os 5 cafés especiais de forma idempotente (`ON CONFLICT (id) DO NOTHING`).
- **Resiliência na API ([`repository.py`](../../integrante_B/api/src/repository.py)):**
  - **Startup seguro:** se a API subir alguns segundos antes do PostgreSQL terminar de inicializar, `PostgresRepository.initialize()` tenta até `DB_INIT_RETRIES` (padrão `10` vezes). Mesmo se o banco estiver completamente desligado no startup, a API não trava/morre — ela sobe respondendo `503` no `/health` e cria o schema automaticamente assim que o banco ficar online.
  - **Recuperação após Falha 4 (`docker stop` / `docker start`):** usamos `check=ConnectionPool.check_connection` e `pool_timeout=3.0s`. Quando o banco para, as requisições falham rápido com `503` (sem travar 30s) e, quando o banco volta, conexões quebradas são descartadas automaticamente sem precisar reiniciar a API.

---

## 3. Os 3 Sinais, Métricas Prometheus e Cardinalidade

1. **Métricas (números agregados ao longo do tempo — coleta *Pull*):**
   O Prometheus bate a cada 15s em `GET /metrics`. Em [`metrics.py`](../../integrante_B/api/src/metrics.py):
   - **`Counter` (só sobe):** `http_requests_total{rota, metodo, status}`, `pedidos_criados_total`, `pedidos_valor_reais_total`.
   - **`Histogram` (faixas/buckets para medir latência `p95`):** `http_request_duration_seconds{rota}` com bucket específico em `0.3` (300 ms, alinhado ao SLO). A média engana quando poucos clientes demoram muito; o `p95` mostra o limite de tempo dos 95% mais rápidos.
   - **`Gauge` (sobe e desce):** `db_pool_conexoes_em_uso` mostra quantas conexões do pool estão abertas e ocupadas naquele instante.
2. **Logs (eventos detalhados em JSON no `stdout`):** contêm `timestamp`, `nivel`, `rota`, `status`, `duracao_ms`, `pedido_id`, `trace_id`. Em Docker, não salvamos em arquivo interno descartável: imprimimos no `stdout` para o coletor enviar ao Loki.
3. **Traces (bônus):** caminho `web → api → db` amarrado pelo `trace_id` já propagado entre Nginx e FastAPI.

### Por que nunca colocar `pedido_id` ou `cliente` como label no Prometheus?
Cada combinação única de labels vira uma **série temporal nova na RAM do Prometheus** (*alta cardinalidade*). Colocar `pedido_id` criaria milhares de séries infinitas e derrubaria o Prometheus por falta de memória. Dados individuais sempre vão para os **logs JSON**, nunca para labels de métricas.

### Por que `/health`, `/metrics` e `/admin/caos` são imunes ao `/admin/caos`?
Em [`chaos.py`](../../integrante_B/api/src/chaos.py):
- Se `taxa_erro=1.0` afetasse `/admin/caos`, não seria possível desligar o caos depois.
- Se afetasse `/metrics`, o Prometheus ficaria cego durante a falha.
- `/health` precisa medir exclusivamente a saúde do banco (`200` com banco vivo, `503` com banco fora), diferenciando Falha 4 (banco parado) das Falhas 5 e 6 (caos na API).

---

## 4. Simulado de Arguição (Perguntas da Parte B)

1. **Qual a diferença entre Monitoramento e Observabilidade?**
   > Monitoramento verifica estados conhecidos ("o serviço responde?", "o disco encheu?"). Observabilidade permite investigar a causa raiz de falhas desconhecidas combinando métricas (o que e quando piorou), logs (detalhe da requisição que falhou) e traces.
2. **Coleta Pull vs. Push: qual o Prometheus usa e qual a vantagem?**
   > Usa **Pull (*scraping*)**: o Prometheus busca os dados em `/metrics`. A API não precisa conhecer o IP do Prometheus e, se o alvo cair ou a WAN romper, o Prometheus detecta imediatamente com `up == 0`.
3. **Por que `http_request_duration_seconds` é um Histograma e não um Gauge com a média?**
   > Porque médias escondem picos de lentidão (*tail latency*). Buckets permitem calcular percentis como `p95` no Prometheus (`histogram_quantile`).
4. **Como o código garante baixa cardinalidade nas métricas HTTP?**
   > Usando apenas `rota` (template normalizado via `resolve_route_path`, jogando URLs inválidas para `/unmatched`), `metodo` e `status`, e deixando `pedido_id` e `cliente` exclusivamente nos logs JSON.
