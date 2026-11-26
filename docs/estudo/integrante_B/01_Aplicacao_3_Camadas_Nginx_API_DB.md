# B1 — Aplicação em 3 Camadas: Nginx, API FastAPI e PostgreSQL (Do Zero)

A melhor forma de entender programação web sem decorar teoria é **seguir o caminho de um único clique no botão "Fazer Pedido"** na tela da loja (`http://127.0.0.1:8088`).

---

## 1. O Básico: Cliente, Servidor, HTTP, JSON e Raio-X

### Por que isso existe?
O seu navegador (Chrome/Edge) mostra telas bonitas para humanos, mas o banco de dados não fala HTML. Eles conversam usando um idioma padrão chamado **HTTP** trocando mensagens em texto estruturado chamado **JSON**.

Toda conversa HTTP tem 4 peças simples:
1. **IP + Porta:** onde o programa atende (como `IP = prédio` e `Porta = número da sala`; ex.: Nginx na porta `80`, API Python na porta `8000`, PostgreSQL na porta `5432`).
2. **Método (verbo):**
   - **`GET`** = só consultar/ler (ex.: `GET /produtos` lista os 5 cafés).
   - **`POST`** = enviar dados para criar ou mudar algo (ex.: `POST /pedidos` cria um pedido; `POST /admin/caos` liga defeitos simulados).
3. **Status Code (o código de 3 dígitos da resposta):**
   - **`200 OK`** = deu certo.
   - **`201 Created`** = algo novo foi gravado no banco com sucesso.
   - **`404 Not Found`** = pediu algo que não existe (ex.: café ID `9999`).
   - **`500 Internal Server Error`** = erro dentro da API (simulado na Falha 6).
   - **`503 Service Unavailable`** = a API está viva, mas o banco atrás dela caiu (Falha 4).
4. **JSON:** texto organizado em `"chave": valor` (ex.: `{"produto_id": 1, "quantidade": 2}`).

### Veja funcionando agora na sua tela (10 segundos)
1. Abra **`http://127.0.0.1:8088`** no navegador.
2. Clique em **"Fazer Pedido"** em qualquer café.
3. Clique na aba **"Laboratório de Caos & Raio-X HTTP"**: ali você vê o método exato (`POST /pedidos`), o status (`201`), o tempo em `ms`, o **`X-Trace-Id`** e o **JSON completo** devolvido pela API!

---

## 2. Docker e por que instalamos `iproute2`

- **VM vs. Contêiner Docker:** uma VM simula um PC inteiro (gasta ~1 GB de RAM cada). Um contêiner compartilha o mesmo Linux da máquina e sobe em 1 segundo gastando poucos MB.
- **`Dockerfile` → Imagem → Contêiner:** o `Dockerfile` é a **receita**, `docker build` cria o **bolo pronto (imagem)** e `docker run`/`compose` coloca o **bolo na mesa rodando (contêiner)**.
- **Por que `iproute2` está em todos os nossos Dockerfiles (`web`, `api`, `db`, `loadgen`)?** Porque imagens enxutas (`alpine`, `python:slim`) não vêm com o comando `ip`. Quando o Containerlab subir os contêineres na topologia da dupla, ele roda `ip addr add` e `ip route add` lá dentro — sem `iproute2`, a rede não subiria!

---

## 3. Por que dividimos a Loja em 3 Camadas (`web → api → db`)?

```text
  Navegador / Filial
         │  HTTP :80 (loja.cafeplanalto.lab)
         ▼
  [1] WEB — Nginx (172.20.10.20)
         │  Recepção: entrega index.html, repassa /produtos e /pedidos, cria X-Trace-Id
         ▼  HTTP :8000
  [2] API — FastAPI + Uvicorn (172.20.10.21)
         │  Cérebro: regras da loja, métricas, logs JSON e botão /admin/caos
         ▼  TCP :5432
  [3] DB — PostgreSQL (172.20.10.22)
            Cofre: guarda produtos e pedidos no disco mesmo se reiniciar
```

### Camada 1: `web` — Nginx ([`integrante_B/web/`](../../../integrante_B/web/))
- **Por que não ligar direto na API?** O Nginx funciona como **recepcionista (proxy reverso)** na porta padrão `80`:
  - Quem abre `/` recebe o site visual ([`index.html`](../../../integrante_B/web/html/index.html), 100% offline sem depender da internet).
  - Quem chama `/produtos`, `/pedidos`, `/health` ou `/admin/caos` é encaminhado para a API na porta `8000` ([`default.conf.template`](../../../integrante_B/web/templates/default.conf.template)).
  - Ele também carimba um código de rastreio **`X-Trace-Id`** em cada requisição e expõe um painel técnico interno na porta `8080/nginx_status` (`stub_status`) para monitoramento.
- **Valide em 10 segundos:** abra `http://127.0.0.1:8089/nginx_status` e veja o total de requisições entrando em tempo real.

### Camada 2: `api` — FastAPI ([`integrante_B/api/`](../../../integrante_B/api/))
- **FastAPI** define as rotas (`/produtos`, `/pedidos`, `/health`, `/metrics`, `/admin/caos`). **Pydantic** ([`models.py`](../../../integrante_B/api/src/models.py)) barra dados inválidos antes de entrarem (ex.: quantidade negativa). **Uvicorn** recebe várias conexões ao mesmo tempo de forma assíncrona (`await asyncio.sleep` faz esperar sem travar outros clientes).
- **O segredo do `observability_and_chaos_middleware` ([`main.py`](../../../integrante_B/api/src/main.py)):** imagine uma **catraca na entrada/saída** da API. Toda requisição passa por ela:
  1. Liga um cronômetro e lê o `X-Trace-Id`.
  2. Se a rota não for protegida, aplica a lentidão ou erro 500 do `/admin/caos`.
  3. Executa a rota e, na saída, **soma os contadores do Prometheus + imprime 1 linha JSON no terminal (`stdout`)**.

### Camada 3: `db` — PostgreSQL ([`integrante_B/db/`](../../../integrante_B/db/))
- O [`init.sql`](../../../integrante_B/db/init.sql) cria as tabelas `produtos` e `pedidos` e cadastra os 5 cafés.
- **O que é o Pool de Conexões ([`repository.py`](../../../integrante_B/api/src/repository.py))?** Abrir uma porta nova para o banco a cada clique é lento; o *pool* deixa alguns "guichês abertos" prontos para reuso.
- **Por que nossa API não morre na Falha 4 (`docker stop db`)?** Configuramos `pool_timeout=3.0s` e `check_connection`. Se o banco cair, a API devolve **`503 Service Unavailable`** rapidamente (sem travar) e, quando o banco volta, reconecta sozinha sem precisar reiniciar a API!
- **Valide + "E se eu quebrar?":** pare o banco (`docker stop cafeplanalto-dev-db`) e clique em **"Atualizar saúde"** no topo da loja — o badge fica vermelho (`503 / unavailable`). Religue o banco e clique de novo — volta para verde (`ok / postgres`)!

---

## 4. Os 3 Sinais: Métricas, Logs JSON, Cardinalidade e Caos

### 4.1 Os 3 tipos de métricas em [`metrics.py`](../../../integrante_B/api/src/metrics.py)
| Tipo | Analogia | Nossa métrica | Para que serve no painel |
| --- | --- | --- | --- |
| **`Counter`** | **Hodômetro do carro** (só sobe) | `http_requests_total`, `pedidos_criados_total`, `pedidos_valor_reais_total` | Calcular pedidos/min e taxa de erro usando `rate()`. |
| **`Histogram`** | **Baldes de tempo** (faixas de ms) | `http_request_duration_seconds` (com balde exato em `0.3s`) | Calcular o **`p95`** (*95% dos clientes foram atendidos até X ms*). A média engana se 1 pessoa esperar 10s e 99 esperarem 10ms! |
| **`Gauge`** | **Velocímetro** (sobe e desce) | `db_pool_conexoes_em_uso` | Mostrar quantas conexões do banco estão ocupadas **neste exato segundo**. |

### 4.2 Por que `pedido_id` e `cliente` são PROIBIDOS como labels no Prometheus?
Cada combinação diferente de labels (`{rota="/pedidos", status="201"}`) vira uma **série nova na memória RAM do Prometheus**. Se colocássemos `pedido_id`, após 100.000 pedidos o Prometheus teria 100.000 séries novas eternas e **travaria por falta de memória** (*alta cardinalidade*).
- **Regra:** números gerais ficam nas **métricas**; detalhes únicos (`pedido_id`, `cliente`, `trace_id`) vão para os **logs JSON**.

### 4.3 Por que `/health`, `/metrics` e `/admin/caos` são IMUNES ao caos ([`chaos.py`](../../../integrante_B/api/src/chaos.py))?
1. **`/admin/caos` imune:** se `taxa_erro=1.0` (100% de erro) afetasse `/admin/caos`, você ficaria trancado para fora e nunca mais conseguiria desligar o caos!
2. **`/metrics` imune:** se `/metrics` desse 500, o Prometheus ficaria cego e não enxergaria os erros acontecendo.
3. **`/health` imune:** ele testa só o banco (`200` com banco vivo, `503` com banco morto), permitindo saber se a falha é na API (Falhas 5/6) ou no PostgreSQL (Falha 4).
