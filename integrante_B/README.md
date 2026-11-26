# Loja Café Planalto — API (Semana 1 / Integrante B)

API em **Python + FastAPI** da loja virtual fictícia **Café Planalto**, desenvolvida com foco em observabilidade (métricas Prometheus + logs JSON estruturados) e engenharia de caos controlada para o trabalho prático de Monitoramento e Observabilidade.

## Estrutura do projeto

- `src/config.py`: carregamento de variáveis de ambiente (`.env`).
- `src/models.py`: modelos Pydantic de produtos, pedidos, saúde e caos.
- `src/repository.py`: persistência em memória (Semana 1) e suporte pronto para PostgreSQL via `DATABASE_URL` (Semana 2).
- `src/metrics.py`: métricas obrigatórias no formato Prometheus (`prometheus_client`).
- `src/logging_json.py`: formatação de logs estruturados em JSON para `stdout`.
- `src/chaos.py`: estado de injeção de caos (`latencia_ms` e `taxa_erro`) com rotas de observabilidade imunes.
- `src/main.py`: aplicação FastAPI, middleware unificado e endpoints REST.
- `Dockerfile`: imagem baseada em `python:3.12-slim` (multi-arch `amd64`/`arm64`) com `iproute2` e `curl` para compatibilidade com Containerlab.

## Como executar com Docker

```bash
docker build -t cafeplanalto/api:latest .
docker run --rm -p 8000:8000 --name cafeplanalto-api cafeplanalto/api:latest
```

## Como executar localmente (Python / venv)

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000 --no-access-log
```

## Variáveis de ambiente

Consulte [`.env.example`](.env.example). Na Semana 1, com `DATABASE_URL` vazio, a API utiliza automaticamente o repositório em memória.

## Endpoints

| Método e Rota | Descrição |
| --- | --- |
| `GET /` | Informações básicas da API e lista de rotas |
| `GET /produtos` | Lista o catálogo estático de cafés da Café Planalto |
| `POST /pedidos` | Registra um novo pedido e atualiza métricas de negócio |
| `GET /pedidos` | Lista os pedidos registrados |
| `GET /health` | Retorna `200` se o backend de dados responde ou `503` se indisponível |
| `GET /metrics` | Expõe métricas no formato Prometheus |
| `GET /admin/caos` | Consulta a configuração atual de caos |
| `POST /admin/caos` | Liga ou desliga latência artificial (`latencia_ms`) e erros (`taxa_erro`) |

### Comandos rápidos (`curl`) para demonstração

```bash
# 1. Verificar saúde da API
curl -i http://localhost:8000/health

# 2. Listar catálogo de cafés
curl -s http://localhost:8000/produtos

# 3. Criar um pedido
curl -s -X POST http://localhost:8000/pedidos \
  -H "Content-Type: application/json" \
  -H "X-Trace-Id: demo-trace-001" \
  -d '{"produto_id": 1, "quantidade": 2, "cliente": "filial-balcao"}'

# 4. Injetar caos (800ms de latência e 20% de erro HTTP 500)
curl -s -X POST http://localhost:8000/admin/caos \
  -H "Content-Type: application/json" \
  -d '{"latencia_ms": 800, "taxa_erro": 0.2}'

# 5. Desligar caos
curl -s -X POST "http://localhost:8000/admin/caos?latencia_ms=0&taxa_erro=0"

# 6. Inspecionar métricas Prometheus
curl -s http://localhost:8000/metrics
```

## Sinais de observabilidade

### Métricas Prometheus (`GET /metrics`)

- `http_requests_total{rota, metodo, status}` (`Counter`)
- `http_request_duration_seconds{rota}` (`Histogram` com bucket `0.3` para SLO p95 < 300ms)
- `pedidos_criados_total` (`Counter`)
- `pedidos_valor_reais_total` (`Counter`)
- `db_pool_conexoes_em_uso` (`Gauge`)

### Logs estruturados (JSON no `stdout`)

Cada requisição gera uma linha JSON contendo `timestamp`, `nivel`, `mensagem`, `rota`, `metodo`, `status`, `duracao_ms` e, quando presente no cabeçalho `traceparent` ou `X-Trace-Id`, `trace_id`.

## Testes automatizados

```bash
pip install pytest httpx
pytest -v
```
