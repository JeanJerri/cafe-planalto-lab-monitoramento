# Guia Completo de Estudo (Do Zero) — Aplicação Loja Café Planalto (Integrante B / Semana 1)

Este guia foi feito como uma **escada passo a passo para quem é leigo**. Cada capítulo só usa conceitos que já foram explicados nos capítulos anteriores, e a parte final mostra **exatamente qual terminal abrir, em qual pasta entrar e o que digitar no seu computador** para testar e apresentar.

---

## Etapa 1 — O Mapa Geral do Trabalho (A História da Café Planalto)

A empresa fictícia **Café Planalto** (de Vitória da Conquista - BA) vende cafés especiais pela internet. Ela tem:
- **Matriz:** onde ficam os servidores da loja virtual (site, API e banco de dados) e as ferramentas de monitoramento.
- **Filial:** onde ficam os atendentes e um cliente simulado comprando café pela rede, ligado à Matriz por um enlace de longa distância (**WAN**).

No último mês, a loja caiu duas vezes e a diretoria só descobriu quando clientes reclamaram. A missão da dupla é construir esse ambiente virtual no computador e deixá-lo **visível** usando duas ferramentas:
1. **Zabbix** (foco em rede, servidores, roteadores e switches — Semanas 2–3).
2. **Prometheus + Grafana + Loki** (foco na aplicação, contêineres, métricas, logs e alertas — Semanas 2–3).

Na **Semana 1**, a dupla dividiu o trabalho em duas metades independentes:
- **Integrante A (Infraestrutura / Rede):** construiu as "estradas" (roteadores, cabos virtuais e rotas estáticas).
- **Integrante B (Aplicação — você):** construiu o "prédio da loja" (a API da Café Planalto) já equipado com **sensores** (métricas e logs) e um **botão de defeito controlado** (`/admin/caos`) para simular problemas na apresentação.

---

## Etapa 2 — Como uma Aplicação Web e uma API Funcionam (Do Zero)

Antes de abrir qualquer arquivo de código, entenda como dois programas conversam pela rede.

### 2.1 Cliente, Servidor, IP e Porta
Imagine um prédio comercial:
- **Cliente:** quem faz o pedido (seu navegador Chrome/Edge, o comando `curl`, ou o computador da filial).
- **Servidor:** o computador/programa que fica esperando pedidos para responder (a nossa API).
- **Endereço IP** (ex.: `127.0.0.1` ou `172.20.10.21`): é o **endereço da rua e número do prédio** onde o servidor mora.
  - **`localhost` ou `127.0.0.1`** é um endereço especial que sempre significa **"este meu próprio computador agora"**.
- **Porta** (ex.: `:8000`): dentro do prédio (IP), podem rodar vários programas ao mesmo tempo. A porta é o **número do apartamento** (nossa API atende na porta `8000`).
  - Por isso acessamos `http://localhost:8000` (computador local, porta 8000) ou `http://172.20.10.21:8000` (servidor `api` na rede da Matriz, porta 8000).

### 2.2 O que é HTTP e API REST?
- **Site comum:** quando você entra em um site, o servidor devolve uma página visual (HTML) para humanos lerem.
- **API (Application Programming Interface):** em vez de devolver telas bonitas, o servidor devolve **dados puros** para outros programas usarem (ou para um site moderno montar a tela).
- **HTTP** é o idioma (protocolo) usado nessa conversa. Toda conversa HTTP tem:
  1. **Método (verbo):** o que o cliente quer fazer:
     - **`GET`:** "me dê/liste uma informação" (não cria nem altera nada; ex.: listar cafés).
     - **`POST`:** "envie estes dados para criar ou executar algo" (ex.: criar um pedido ou ligar o caos).
  2. **Rota / Endpoint:** o "balcão" específico dentro da API (ex.: `/produtos`, `/pedidos`, `/health`, `/metrics`, `/admin/caos`).
  3. **Query Params (parâmetros na URL):** dados extras depois do `?` na URL. Exemplo: `POST /admin/caos?latencia_ms=0&taxa_erro=0`.
  4. **Headers (Cabeçalhos):** etiquetas coladas fora do "envelope" da requisição (ex.: `Content-Type: application/json` avisando que o conteúdo é JSON, ou `X-Trace-Id: demo-01` para rastreamento).
  5. **Body (Corpo):** o conteúdo enviado dentro do envelope (geralmente em requisições `POST`), escrito em **JSON**.
  6. **Status Code (Código de Resposta):** número de 3 dígitos que diz o resultado imediato:
     - **`200 OK`**: tudo certo.
     - **`201 Created`**: algo novo foi criado com sucesso (usado em `POST /pedidos`).
     - **`404 Not Found`**: o item pedido não existe (ex.: pedir o café de `produto_id: 9999`).
     - **`500 Internal Server Error`**: erro interno dentro do servidor (também simulado de propósito pelo `/admin/caos`).
     - **`503 Service Unavailable`**: a API está viva, mas um serviço essencial atrás dela (como o banco de dados) está fora do ar.

### 2.3 O que é JSON?
**JSON** (*JavaScript Object Notation*) é apenas um formato de texto organizado em pares `"chave": valor` entre chaves `{ }`, fácil de ler por humanos e por qualquer linguagem de programação:

```json
{
  "produto_id": 1,
  "quantidade": 2,
  "cliente": "filial-balcao"
}
```

---

## Etapa 3 — As Peças do Código Python da Nossa API

Agora que você entende HTTP e JSON, veja para que serve cada tecnologia usada na pasta `src/`:

### 3.1 Ambiente Virtual (`.venv`) e `requirements.txt`
- Se você instalar bibliotecas Python diretamente no Windows, projetos diferentes podem brigar por versões diferentes.
- O **`.venv`** é uma "caixinha isolada" dentro da pasta do projeto com uma cópia própria do Python e das bibliotecas instaladas só para a Café Planalto.
- O arquivo **`requirements.txt`** é a lista de compras dessas bibliotecas (ex.: `fastapi`, `uvicorn`, `prometheus-client`, `pydantic`, `python-dotenv`, `psycopg`).

### 3.2 FastAPI, Pydantic e Uvicorn
- **FastAPI:** é o framework em Python onde declaramos as rotas (`@app.get("/produtos")`, `@app.post("/pedidos")`). Além disso, ele gera sozinho uma página interativa de testes em `http://localhost:8000/docs` (Swagger UI).
- **Pydantic** (`src/models.py`): é o "segurança da porta" dos dados. Se alguém enviar `quantidade: -5` ou `taxa_erro: 2.0` (inválido, pois o máximo é `1.0`), o Pydantic rejeita automaticamente antes de entrar no código da loja.
- **Uvicorn:** o Python sozinho não sabe escutar uma placa de rede nem gerenciar dezenas de conexões HTTP ao mesmo tempo. O **Uvicorn** é o servidor web (ASGI) que fica escutando a porta `8000`, traduz os bytes da rede em objetos HTTP e entrega para o FastAPI responder.

### 3.3 Middleware e `lifespan`
- **`lifespan`** (em `src/main.py`): é o código que roda uma única vez quando a API **liga** (inicializa o repositório/banco e grava o log de `startup`) e uma única vez quando ela **desliga** (fecha conexões com segurança e grava o log de `shutdown`).
- **Middleware** (`observability_and_chaos_middleware` em `src/main.py`): imagine uma **catraca obrigatória** antes e depois de todos os balcões da loja:
  - **Na entrada:** ela dispara um cronômetro, lê o `trace_id` do cabeçalho e verifica se deve injetar lentidão ou erro simulado (caos).
  - **Na saída:** ela para o cronômetro, soma os contadores do Prometheus e imprime 1 linha de log em JSON no terminal.
  - Graças ao middleware, não precisamos repetir código de log e tempo em cada rota!

### 3.4 Código Síncrono vs. Assíncrono (`await asyncio.sleep`)
- Imagine um garçom **síncrono (bloqueante):** quando um cliente pede um café demorado, o garçom fica parado olhando a cafeteira e **não atende mais ninguém** até o café ficar pronto.
- No modo **assíncrono (`async` / `await`)**: quando o caos aplica `latencia_ms=800`, nosso middleware usa `await asyncio.sleep(0.8)`. Isso faz a requisição atual esperar 800 milissegundos sem travar o servidor para os outros clientes que chegam ao mesmo tempo.

### 3.5 Variáveis de Ambiente (`.env`) e Pool de Conexões (Semana 1 vs. Semana 2)
- **Variáveis de ambiente (`.env`):** são configurações externas passadas para o programa sem alterar o código-fonte (ex.: porta `8000`, nível de log `INFO`, endereço do banco `DATABASE_URL`). O arquivo `.env.example` mostra todas as variáveis aceitas com comentários explicativos.
- **Repositório desacoplado (`src/repository.py`):**
  - **Na Semana 1 (`DATABASE_URL` vazio):** a API usa o `InMemoryRepository` (os 5 cafés ficam na memória RAM e os pedidos também). Assim você testa tudo hoje sem precisar subir um servidor PostgreSQL.
  - **Na Semana 2 (`DATABASE_URL` preenchido):** basta configurar o endereço do PostgreSQL na variável de ambiente e a API ativa sozinha o `PostgresRepository`, cria as tabelas no banco e passa a usar um **Pool de Conexões**.
- **O que é um Pool de Conexões?** Abrir uma conexão nova com o banco de dados a cada clique é lento. Um *pool* mantém algumas conexões já abertas e reutilizáveis ("guichês abertos"). A métrica `db_pool_conexoes_em_uso` mostra quantos desses guichês estão ocupados naquele segundo.

---

## Etapa 4 — Docker Explicado do Zero

### 4.1 Máquina Virtual vs. Contêiner Docker
- **Máquina Virtual (VM):** simula um computador inteiro do zero (BIOS, disco virtual, sistema operacional completo). Cada VM consome facilmente 1 GB a 2 GB de RAM. Subir 13 servidores em VMs travaria um notebook comum.
- **Contêiner Docker:** isola apenas a aplicação e suas dependências em uma "caixa fechada", compartilhando o mesmo núcleo (kernel) do Linux da máquina hospedeira. Um contêiner sobe em 1 segundo e gasta poucos megabytes de RAM.

### 4.2 `Dockerfile`, Imagem e Contêiner
- **`Dockerfile`:** é a receita passo a passo de texto dizendo o que instalar.
- **Imagem (`cafeplanalto/api:latest`):** é o pacote pronto gerado a partir da receita (`docker build`).
- **Contêiner (`clab-cafeplanalto-api`):** é a imagem rodando na memória (`docker run` ou Containerlab).

### 4.3 Entendendo cada linha do nosso `Dockerfile`
```dockerfile
FROM python:3.12-slim
```
Começa de um Linux Debian mínimo já com Python 3.12 (compatível com PCs `amd64` e Macs M1-M4 `arm64`).

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
```
`PYTHONUNBUFFERED=1` é muito importante: obriga o Python a imprimir os logs imediatamente na tela (`stdout`) sem segurar em buffer na memória.

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends iproute2 curl \
    && rm -rf /var/lib/apt/lists/*
```
- **`iproute2`:** instala o comando `ip` (`ip addr`, `ip route`). **Por que isso é obrigatório?** Porque quando a Integrante A sobe o laboratório no Containerlab, ele executa `ip addr add 172.20.10.21/24 dev eth1` e `ip route add ...` dentro do contêiner da API. Imagens Python `slim` não vêm com `ip`, então sem `iproute2` a rede da dupla não subiria!
- **`curl`:** ferramenta para testar HTTP dentro do próprio contêiner se precisar.

```dockerfile
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
```
- `--host 0.0.0.0`: aceita conexões vindas de fora do contêiner (pela rede WAN e pelo navegador). Se fosse `127.0.0.1`, ninguém de fora conseguiria acessar a loja!
- `--no-access-log`: desliga o log padrão em texto do Uvicorn para que saiam **apenas** logs JSON estruturados.

---

## Etapa 5 — Monitoramento vs. Observabilidade e os 3 Sinais

| Conceito | Pergunta que responde | Exemplo prático no trabalho |
| --- | --- | --- |
| **Monitoramento** | *"A loja está no ar? O servidor ou disco encheu?"* | Checar se a porta responde, se o ping chega ou se `/health` retorna `200`. |
| **Observabilidade** | *"Por que a loja está lenta ou devolvendo erro agora, e para quem?"* | Ver no gráfico que a latência p95 subiu às 14:21, clicar no intervalo e ler o log JSON exato da requisição que deu erro 500. |

**Analogia:** Monitoramento é a luz vermelha no painel do carro ("problema no motor"). Observabilidade é ter os sensores gravando temperatura, pressão e códigos de falha para você abrir o capô sabendo exatamente qual peça trocar.

### Os 3 Sinais (Pilares) na prática de uma compra de café
Quando o cliente da filial faz `POST /pedidos`:
1. **Métricas (números agregados ao longo do tempo):** *"Às 14:21 entraram 15 pedidos/min e 20% deram erro 500."* Baratas para guardar e ideais para gráficos e alertas.
2. **Logs (registro detalhado de cada evento):** *"Às 14:21:10.028 o pedido `id=1`, `produto_id=1`, `valor=97.8`, `trace_id=demo-01` foi confirmado em `1.81 ms`."* Ideais para achar a causa raiz.
3. **Traces (rastreamento ponta a ponta — bônus):** desenham a linha do tempo de uma requisição atravessando `web (Nginx) -> api (FastAPI) -> db (PostgreSQL)`. Na Semana 1 ainda não enviamos traces ao Jaeger/Tempo, mas nossa API já extrai o **`trace_id`** dos cabeçalhos HTTP `traceparent` (W3C) ou `X-Trace-Id` e grava esse ID nos logs JSON para permitir correlação.

---

## Etapa 6 — Prometheus, Tipos de Métricas, Percentil p95, SLO e Cardinalidade

### 6.1 O que é uma Série Temporal e o PromQL?
- **Série Temporal:** é simplesmente uma tabela com `(horário, valor)` registrada ao longo do tempo (ex.: `14:20:00 -> 10 pedidos`, `14:20:15 -> 14 pedidos`).
- **PromQL** (*Prometheus Query Language*): é a linguagem de consulta usada pelo Prometheus e pelo Grafana para transformar essas séries em gráficos (taxas por segundo, porcentagem de erro, percentis).

### 6.2 Coleta Pull (Scraping) vs. Coleta Push
- **Push (empurrar):** a aplicação envia os dados para o servidor de monitoramento (como um agente ativo do Zabbix enviando dados para o Zabbix Server). A aplicação precisa saber o IP do servidor.
- **Pull / Scraping (puxar — usado pelo Prometheus):** a aplicação **não conhece o Prometheus**. Ela apenas deixa os números expostos na página `GET /metrics`. A cada 15 segundos, o Prometheus bate em `http://172.20.10.21:8000/metrics` e "raspa" (*scrape*) os números.
- **Vantagem enorme:** se a API travar ou o cabo WAN da matriz/filial cair, o Prometheus não consegue ler `/metrics` e marca imediatamente a métrica interna `up == 0`.

### 6.3 Os 3 Tipos de Métricas em `src/metrics.py`

#### 1) `Counter` (Contador — só sobe!)
Pense no **hodômetro (quilometragem total)** de um carro: ele só sobe (e só zera se o contêiner reiniciar).
Nossa API tem 3 contadores obrigatórios:
- **`http_requests_total{rota, metodo, status}`:** conta todas as requisições por rota, método HTTP e código de status.
  - Exemplo real impresso em `/metrics`:
    ```text
    http_requests_total{metodo="GET",rota="/produtos",status="200"} 1.0
    http_requests_total{metodo="POST",rota="/pedidos",status="201"} 1.0
    ```
- **`pedidos_criados_total`:** total acumulado de pedidos confirmados.
- **`pedidos_valor_reais_total`:** faturamento total acumulado em `R$`.
- *Por que usar `rate()`?* Se o contador diz "já houve 5.000 pedidos desde ontem", isso não mostra o ritmo de agora. No Grafana, `rate(http_requests_total[1m])` calcula **quantas requisições por segundo** aconteceram no último minuto.

#### 2) `Histogram` (Histograma — mede quanto tempo demorou + Percentil p95)
Por que não usar apenas a **média** do tempo de resposta?
- Imagine 99 clientes atendidos em `10 ms` e 1 cliente travado por `10.000 ms` (10 segundos). A média seria ~`110 ms` e **esconderia** que alguém esperou 10 segundos!
- Para enxergar o comportamento real sem guardar milhões de tempos individuais, o **Histograma** divide o tempo em faixas acumulativas chamadas **buckets** (`le` significa *less than or equal* = "menor ou igual a X segundos").

**Exemplo numérico passo a passo:**
Suponha que 5 requisições para `/produtos` demoraram: `0.004s`, `0.02s`, `0.15s`, `0.25s`, `0.80s`.
Nossa métrica `http_request_duration_seconds{rota="/produtos"}` tem os buckets `0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 2.5, 5.0` e `+Inf`:
- `le="0.005"` (<= 5 ms): **1** requisição (`0.004s`)
- `le="0.025"` (<= 25 ms): **2** requisições (`0.004s` e `0.02s`)
- `le="0.2"` (<= 200 ms): **3** requisições
- `le="0.3"` (<= 300 ms): **4** requisições (todas menos a de `0.80s`!)
- `le="1.0"` (<= 1.000 ms): **5** requisições (todas)
- `_count`: **5** (total de requisições)
- `_sum`: **1.224** (soma dos tempos em segundos)

**O que é o famoso `p95` (Percentil 95)?**
- Ordene as últimas 100 requisições da mais rápida para a mais lenta. O valor na posição **95** é o **p95**: significa que **95% dos clientes foram atendidos até aquele tempo** (e apenas os 5% piores casos demoraram mais).
- **Por que colocamos o bucket `0.3` (300 ms)?** O roteiro sugere o objetivo de **latência p95 abaixo de 300 ms**. Ter exatamente o corte `le="0.3"` deixa o cálculo `histogram_quantile(0.95, ...)` no Grafana muito mais preciso!
- **E os buckets `0.75` e `1.0`?** Na Falha 5, o professor injeta `latencia_ms=800` (`0.8s`), que cai exatamente entre `0.75` e `1.0`, fazendo o p95 disparar acima de `0.3s` e acionar o alerta.

#### 3) `Gauge` (Medidor instantâneo — sobe e desce)
Pense no **velocímetro ou marcador de combustível**: mostra o valor exato **agora**.
- **`db_pool_conexoes_em_uso`:** na Semana 1 (sem PostgreSQL) fica em `0.0`. Na Semana 2 (com PostgreSQL), sobe quando uma consulta pega uma conexão e desce quando devolve. Se ficar grudado no máximo do pool, significa que o banco saturou.

### 6.4 SLI, SLO e Orçamento de Erro (Error Budget)
- **SLI (*Indicator* — o que você mede):** *"Neste momento, 99,8% das requisições deram sucesso e o p95 está em 12 ms."*
- **SLO (*Objective* — a meta combinada):** *"A loja deve ter pelo menos 99,5% de disponibilidade e p95 abaixo de 300 ms."*
- **Error Budget (Orçamento de Erro):** é quanto você "pode gastar" de erro sem violar o contrato (`100% - SLO`).
  - Se a meta é **99,5%**, você tem **0,5% de orçamento de erro**.
  - Em **1.000 requisições**, 0,5% equivale a **no máximo 5 erros**. Se o professor ligar a Falha 6 (`taxa_erro=0.2` = 200 erros a cada 1.000 requisições), o orçamento de erro é queimado em segundos!

### 6.5 RED vs. USE vs. Quatro Sinais Dourados

| Método | Onde usa | Sigla / Significado | Na Café Planalto |
| --- | --- | --- | --- |
| **RED** | Aplicação / API (sua parte) | **R**ate (req/s), **E**rrors (taxa de erros), **D**uration (latência) | `http_requests_total` (Rate e Errors) + `http_request_duration_seconds` (Duration) |
| **USE** | Hardware / Redes / Infraestrutura | **U**tilization (% usada), **S**aturation (fila), **E**rrors (descartes/falhas) | CPU/RAM/Disco/Rede no `node_exporter`, `cAdvisor`, Zabbix e `db_pool_conexoes_em_uso` |
| **4 Sinais Dourados** (Google SRE) | Sistemas completos | **Latência**, **Tráfego**, **Erros**, **Saturação** | O RED mede os 3 primeiros; `db_pool_conexoes_em_uso` e recursos do contêiner medem Saturação |

### 6.6 Alta Cardinalidade de Labels (Por que isso derruba o Prometheus?)
Cada conjunto único `{rota="...", metodo="...", status="..."}` vira uma **série temporal diferente** na memória RAM do Prometheus.
- **Baixa cardinalidade (correto):**
  - 7 rotas × 2 métodos × 3 status = ~42 combinações (quase zero memória).
- **Alta cardinalidade (errado e proibido pelo roteiro):**
  - Se você colocasse `pedido_id` ou `cliente` como label (`http_requests_total{pedido_id="98231"}`), após 100.000 pedidos o Prometheus criaria **100.000 séries novas eternas** na RAM, travando o servidor!
- **Como protegemos a API no código:**
  1. `resolve_route_path()` em `src/main.py` garante que apenas rotas definidas (ou `/unmatched` para URLs inválidas) virem label `rota`.
  2. `pedido_id`, `produto_id` e `valor_total_reais` vão **somente para os logs JSON**.
  3. Usamos `prometheus_client` direto em vez da instrumentação automática padrão do `prometheus-fastapi-instrumentator` para obedecer exatamente aos nomes em português do PDF (`rota`, `metodo`, `status`) e evitar o bug de sufixo duplicado `_total_total`.

---

## Etapa 7 — Logs Estruturados em JSON, `stdout`, Loki e `trace_id`

- **O que é `stdout`?** É a "saída padrão" de texto que aparece no terminal quando você roda um programa. Em Docker, tudo que o programa imprime no `stdout` é capturado automaticamente pelo Docker (e visto com `docker logs`).
- **Por que não salvar em arquivo `.log` dentro do contêiner?** Porque contêineres são descartáveis (padrão *12-Factor App*): quando o contêiner é recriado, arquivos internos somem. Mandando para o `stdout`, o coletor (**Promtail** ou **Grafana Alloy**) lê os logs de fora e envia para o **Grafana Loki**.
- **Por que formato JSON em vez de texto solto?**
  - Texto solto: `19/11 14:21 ERRO no pedido 1 cliente filial` (difícil de filtrar automaticamente).
  - JSON estruturado (o que nossa API emite):
    ```json
    {"timestamp": "2026-11-19T14:21:10.028900Z", "nivel": "INFO", "mensagem": "Pedido criado com sucesso", "rota": "/pedidos", "metodo": "POST", "status": 201, "pedido_id": 1, "produto_id": 1, "valor_total_reais": 97.8, "evento": "pedido_criado", "trace_id": "smoke-trace-001"}
    {"timestamp": "2026-11-19T14:21:10.029400Z", "nivel": "INFO", "mensagem": "Requisição HTTP processada", "rota": "/pedidos", "metodo": "POST", "status": 201, "duracao_ms": 1.81, "trace_id": "smoke-trace-001"}
    ```
  - No Loki, basta escrever `{container="clab-cafeplanalto-api"} | json | status >= 500` para filtrar todas as falhas sem precisar de expressões regulares complicadas.
- **O que é `trace_id`?** Funciona como o **código de rastreio dos Correios** de uma requisição. Se o Nginx (ou um cliente no teste) mandar `X-Trace-Id: abc-123` ou `traceparent`, nossa função `extract_trace_id()` em `src/logging_json.py` captura e cola no JSON. Se não houver, o campo é omitido para manter o log limpo.

---

## Etapa 8 — Engenharia de Caos (`/admin/caos`) e `/health`

No roteiro da disciplina, o professor testa falhas reais na aplicação:
- **Falha 4 (`docker stop clab-cafeplanalto-db`):** derruba o banco PostgreSQL.
  - `/health` testa o banco e devolve **`503 Service Unavailable`** (`{"status": "error", "database": "unavailable"}`) + log de erro no `stdout`.
- **Falha 5 (`POST /admin/caos` com `latencia_ms=800`):** adiciona 800 ms de atraso assíncrono nas rotas da loja (`/produtos`, `/pedidos`). A latência p95 dispara acima da meta de 300 ms.
- **Falha 6 (`POST /admin/caos` com `taxa_erro=0.2`):** sorteia 20% das requisições da loja e devolve **`HTTP 500`**, aumentando `http_requests_total{status="500"}`, queimando o orçamento de erro e gerando logs `"nivel": "ERROR"`.

### Por que `/health`, `/metrics` e `/admin/caos` são IMUNES ao caos?
Em `src/chaos.py`, a lista `CHAOS_EXEMPT_PATHS` protege `/health`, `/metrics`, `/admin/caos`, `/docs`, `/redoc` e `/openapi.json`:
1. **`/admin/caos` imune:** se `taxa_erro=1.0` (100% de erro) afetasse `/admin/caos`, você nunca mais conseguiria enviar o comando para desligar o caos!
2. **`/metrics` imune:** se `/metrics` desse 500, o Prometheus perderia a leitura e não enxergaria os erros e a latência da loja subindo.
3. **`/health` imune:** `/health` deve medir **exclusivamente se o banco de dados responde**. Assim, na Falha 4 o `/health` retorna `503` (banco caiu), enquanto nas Falhas 5 e 6 o `/health` continua `200` (provando que o banco está ótimo e o problema está na API).

---

## Etapa 9 — Mapa dos Arquivos e Fluxo Interno

Todos os arquivos da sua parte estão nesta pasta do seu Windows:
`C:\Users\jeanj\Projetos\Projeto_E_Administracao_De_Redes\Projeto_Final\app\`

- `src/config.py` — lê variáveis de ambiente (`.env`) com valores padrão seguros.
- `src/models.py` — valida os dados de entrada/saída com Pydantic.
- `src/repository.py` — gerencia produtos e pedidos (em memória se `DATABASE_URL` estiver vazio; em PostgreSQL se `DATABASE_URL` estiver preenchido).
- `src/metrics.py` — declara as 5 métricas Prometheus obrigatórias.
- `src/logging_json.py` — formata todos os logs da aplicação e do Uvicorn em JSON no `stdout`.
- `src/chaos.py` — guarda `latencia_ms` e `taxa_erro` de forma segura para múltiplas requisições (*thread-safe*).
- `src/main.py` — cria o app FastAPI, registra o middleware e expõe os endpoints.
- `Dockerfile` e `.dockerignore` — empacotam a API em imagem Linux com `iproute2` e `curl`.
- `tests/test_api.py` e `tests/conftest.py` — 5 testes automatizados com `pytest`.
- `.env.example` — modelo das variáveis de ambiente suportadas.

### Fluxo completo dentro do middleware (`src/main.py`)
```text
  Requisição chega (ex.: GET /produtos ou POST /pedidos)
         │
         ▼
  [1] Middleware inicia cronômetro (time.perf_counter) e lê X-Trace-Id / traceparent
         │
         ▼
  [2] Rota está protegida em CHAOS_EXEMPT_PATHS (/health, /metrics, /admin/caos)?
         ├── NÃO ─► Se latencia_ms > 0 ─► await asyncio.sleep(...)
         │       └─► Se sorteio < taxa_erro ─► retorna HTTP 500 simulado
         └── SIM ─► segue direto para o endpoint
         │
         ▼
  [3] Executa o endpoint (lista cafés / salva pedido / testa banco no /health)
         │  (se DatabaseUnavailableError -> retorna HTTP 503)
         ▼
  [4] Se a rota NÃO for "/metrics":
         ├─ Soma +1 em http_requests_total{rota, metodo, status}
         ├─ Registra o tempo gasto em http_request_duration_seconds{rota}
         └─ Imprime 1 linha JSON no stdout (INFO <400, WARNING 4xx, ERROR 5xx)
```

---

## Etapa 10 — Passo a Passo Prático: Onde Ir, Qual Terminal Abrir e Como Testar

Aqui não há nada implícito: siga exatamente na ordem abaixo no seu Windows.

### Passo 10.1 — Abrir o terminal PowerShell e chegar até a pasta do projeto
1. Pressione a tecla **Windows**, digite **`PowerShell`** e abra o **Windows PowerShell** (ou use o terminal integrado dentro do VS Code / IDE).
2. Entre na pasta exata da sua aplicação rodando:

```powershell
cd "C:\Users\jeanj\Projetos\Projeto_E_Administracao_De_Redes\Projeto_Final\app"
```

3. Confirme que você está no lugar certo:

```powershell
pwd
dir
```
- `pwd` deve mostrar `C:\Users\jeanj\Projetos\Projeto_E_Administracao_De_Redes\Projeto_Final\app`.
- `dir` deve listar as pastas `src`, `tests`, `docs`, `.venv` e os arquivos `Dockerfile`, `README.md`, `requirements.txt`.

### Passo 10.2 — Rodar os testes automatizados (`pytest`)
Ainda nesse PowerShell, rode:

```powershell
.\.venv\Scripts\pytest.exe -v
```

**O que deve aparecer no final:**
```text
5 passed, 1 warning in ...s
```
*(Esse comando cria um servidor de teste em memória, testa todos os endpoints, métricas, caos e logs JSON e fecha sozinho — não deixa nada travado.)*

### Passo 10.3 — Subir a API de verdade (Terminal 1)
Para testar com o navegador ou com comandos HTTP reais, suba o servidor Uvicorn neste PowerShell (**vamos chamá-lo de Terminal 1**):

```powershell
.\.venv\Scripts\uvicorn.exe src.main:app --host 0.0.0.0 --port 8000 --no-access-log
```

**Atenção — comportamento normal:**
- Esse **Terminal 1 vai ficar ocupado** (não vai devolver o cursor `PS C:\...>`), porque o servidor está rodando ao vivo esperando requisições!
- Você verá logo de cara as linhas JSON de inicialização (`"Uvicorn running on http://0.0.0.0:8000"`).
- **Deixe o Terminal 1 aberto** para assistir os logs JSON chegando em tempo real sempre que você fizer um teste. Quando quiser desligar o servidor depois, clique dentro do Terminal 1 e aperte **`Ctrl + C`**.

### Passo 10.4 — Testar a API rodando (duas opções)

#### Opção 1 — Pelo Navegador (mais visual para iniciantes)
Com o Terminal 1 rodando, abra o navegador e acesse:
- **`http://localhost:8000/docs`** — abre o painel visual **Swagger UI** onde você pode clicar em `GET /produtos`, `POST /pedidos`, `POST /admin/caos`, clicar em **"Try it out" -> "Execute"** e ver as respostas sem digitar comandos!
- **`http://localhost:8000/health`** — mostra `{"status":"ok","database":"memory"}`.
- **`http://localhost:8000/produtos`** — mostra a lista dos 5 cafés em JSON.
- **`http://localhost:8000/metrics`** — mostra todas as métricas Prometheus em texto puro.

#### Opção 2 — Por um SEGUNDO PowerShell (Terminal 2) com `curl.exe`
> **Pegadinha do Windows PowerShell:** no PowerShell, o comando `curl` sem `.exe` é na verdade um atalho do `Invoke-WebRequest` que exige sintaxe diferente do Linux. Sempre digite **`curl.exe`** (com `.exe`) no PowerShell para usar o `curl` verdadeiro!

1. Abra uma **nova janela do PowerShell** (ou uma nova aba `+` no terminal) — esse será o **Terminal 2**.
2. Execute um comando por vez no Terminal 2 e compare o resultado:

```powershell
# 1. Conferir saúde da API (esperado: HTTP/1.1 200 OK e {"status":"ok","database":"memory"})
curl.exe -i http://localhost:8000/health

# 2. Listar os 5 cafés do catálogo
curl.exe -s http://localhost:8000/produtos

# 3. Criar um pedido enviando cabeçalho X-Trace-Id (esperado: JSON do pedido com valor_total_reais = 97.8)
curl.exe -s -X POST http://localhost:8000/pedidos -H "Content-Type: application/json" -H "X-Trace-Id: aula-01" -d "{\"produto_id\": 1, \"quantidade\": 2, \"cliente\": \"filial-balcao\"}"

# 4. Ligar caos (800ms de lentidão e 50% de chance de erro 500)
curl.exe -s -X POST http://localhost:8000/admin/caos -H "Content-Type: application/json" -d "{\"latencia_ms\": 800, \"taxa_erro\": 0.5}"

# 5. Testar /produtos com caos ligado (rode 2 ou 3 vezes: demora ~0.8s e algumas retornam 500)
curl.exe -i http://localhost:8000/produtos

# 6. Conferir que /health continua 200 OK (imune ao caos!)
curl.exe -i http://localhost:8000/health

# 7. Desligar o caos (sem precisar enviar JSON no corpo)
curl.exe -s -X POST "http://localhost:8000/admin/caos?latencia_ms=0&taxa_erro=0"

# 8. Ver todas as métricas geradas no Prometheus
curl.exe -s http://localhost:8000/metrics
```

Enquanto você executa esses comandos no **Terminal 2**, olhe para o **Terminal 1**: você verá os logs JSON aparecendo ao vivo, incluindo o `"trace_id": "aula-01"` no pedido e `"nivel": "ERROR"` quando a rota `/produtos` der erro `500`!

### Passo 10.5 — Como rodar via Docker no Windows (opcional se usar Docker Desktop)
Se você quiser rodar dentro de um contêiner Docker no Windows:
1. Abra o aplicativo **Docker Desktop** no menu Iniciar e espere o ícone da baleia ficar verde/estável (enquanto estiver fechado, comandos `docker` dão erro de pipe).
2. No PowerShell, dentro de `C:\Users\jeanj\Projetos\Projeto_E_Administracao_De_Redes\Projeto_Final\app`:

```powershell
# Confirmar que o Docker Desktop está ligado
docker info --format "{{.ServerVersion}}"

# Construir a imagem (o ponto "." no final significa "usar o Dockerfile desta pasta")
docker build -t cafeplanalto/api:latest .

# Subir o contêiner mapeando a porta 8000 do contêiner para a porta 8000 do seu Windows
docker run --rm -p 8000:8000 --name cafeplanalto-api cafeplanalto/api:latest
```
*(Lembre de encerrar antes o `uvicorn` com `Ctrl + C` no Terminal 1 para a porta `8000` não estar ocupada!)*

---

## Etapa 11 — Simulado de Arguição Individual (Perguntas e Respostas)

1. **Qual a diferença entre Monitoramento e Observabilidade?**
   > Monitoramento checa se estados conhecidos estão saudáveis ou falhando (ex.: ICMP, porta aberta, `/health` retornando 200). Observabilidade permite investigar a causa raiz de problemas novos analisando externamente os três sinais emitidos pelo sistema: métricas, logs e traces.

2. **O Prometheus usa coleta Push ou Pull? Qual a vantagem disso?**
   > Coleta **Pull** (scraping): o Prometheus busca os dados em `GET /metrics` periodicamente. A API não precisa saber onde o Prometheus mora, e se a API cair ou o enlace WAN parar, o Prometheus detecta automaticamente marcando `up == 0`.

3. **Por que `pedidos_criados_total` é um `Counter`, `http_request_duration_seconds` é um `Histogram` e `db_pool_conexoes_em_uso` é um `Gauge`?**
   > `Counter` é um valor acumulado que só cresce (ótimo para calcular req/s ou pedidos/min com `rate()`). `Histogram` divide tempos em faixas (buckets) para calcular percentis como `p95` (latência dos 95% mais rápidos). `Gauge` representa uma medição instantânea que sobe e desce (conexões abertas agora no banco).

4. **Por que não colocamos `pedido_id` ou `cliente` como label no Prometheus?**
   > Para evitar **alta cardinalidade**. Cada combinação única de valores de labels cria uma série temporal nova na memória do Prometheus; valores infinitos explodem a RAM e derrubam o serviço. Identificadores únicos vão para os logs JSON.

5. **Por que `resolve_route_path()` normaliza a rota na métrica?**
   > Para manter baixa cardinalidade de rotas (URLs inválidas viram `/unmatched`) e porque, quando o middleware de caos intercepta uma requisição antes de chegar ao endpoint, o Starlette ainda não preencheu `request.scope["route"]`.

6. **Por que os logs vão em formato JSON para o `stdout` em vez de um arquivo `.log`?**
   > Seguindo o padrão 12-Factor para contêineres: o Docker captura o `stdout` automaticamente e envia via Promtail/Alloy para o Loki. O formato JSON permite consultar e filtrar campos exatos (`status >= 500`, `trace_id`) no Loki sem expressões regulares frágeis.

7. **Por que `/health`, `/metrics` e `/admin/caos` estão isentos da injeção de caos?**
   > Para conseguir desligar o caos mesmo com `taxa_erro=1.0` (`/admin/caos`), manter o Prometheus coletando os dados da falha (`/metrics`) e garantir que `/health` continue representando apenas a saúde da conexão com o banco (`200` vs `503`).

8. **Por que o `Dockerfile` da API instala o pacote `iproute2`?**
   > Porque a imagem `python:3.12-slim` não traz o utilitário `ip`, e o Containerlab executa `ip addr add` e `ip route add` dentro do contêiner `api` durante a subida da topologia de rede.
