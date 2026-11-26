# Café Planalto — Aplicação 3 Camadas e Carga (Integrante B)

Stack da aplicação da loja virtual **Café Planalto** com foco em observabilidade, resiliência e geração de carga contínua para testes locais no **WSL2 / Docker** antes da integração final na topologia do Containerlab.

## Estrutura de pastas

- [`api/`](api): API REST em Python + FastAPI (catálogo, pedidos, `/health`, `/metrics` Prometheus, `/admin/caos`, logs JSON e pool PostgreSQL resiliente).
- [`web/`](web): Proxy reverso Nginx (`loja.cafeplanalto.lab`), página HTML da loja, logs JSON e endpoint `stub_status` (`:8080/nginx_status`).
- [`db/`](db): Banco PostgreSQL 16 (`postgres:16-alpine` + `iproute2`) com script inicial [`init.sql`](db/init.sql).
- [`loadgen/`](loadgen): Gerador de carga contínuo em `k6` (`5` a `20 req/s`, padrão `10 req/s`) simulando clientes acessando catálogo e criando pedidos.
- [`docker-compose.yml`](docker-compose.yml): Ambiente local isolado do Integrante B (portas ajustadas para não conflitar com a porta `8080` do Zabbix).

## Como subir o ambiente local (WSL2 ou Linux)

> **Dica para WSL2:** mantenha o repositório no sistema de arquivos nativo Linux (`~/...`, não em `/mnt/c/...`) para melhor desempenho de I/O e permissões de contêineres.

```bash
cd integrante_B
cp .env.example .env   # opcional: os padrões já funcionam para desenvolvimento
docker compose up -d --build
```

Portas expostas localmente (`127.0.0.1`):
- **Loja (Nginx):** `http://localhost:8088`
- **Status interno do Nginx (`stub_status`):** `http://localhost:8089/nginx_status`
- **API direta / Swagger:** `http://localhost:8000/docs`
- **Métricas Prometheus da API:** `http://localhost:8000/metrics`

## Testes rápidos e simulação de falhas (Fase 1)

```bash
# 1. Ver saúde via proxy reverso (deve retornar {"status":"ok","database":"postgres"})
curl -i http://localhost:8088/health

# 2. Listar catálogo e criar um pedido pela camada web
curl -s http://localhost:8088/produtos
curl -s -X POST http://localhost:8088/pedidos \
  -H "Content-Type: application/json" \
  -H "X-Trace-Id: teste-web-01" \
  -d '{"produto_id": 1, "quantidade": 2, "cliente": "teste-local"}'

# 3. Ver logs JSON do Nginx e da API, e atividade do gerador de carga
docker logs --tail 5 cafeplanalto-dev-web
docker logs --tail 5 cafeplanalto-dev-api
docker logs --tail 10 cafeplanalto-dev-loadgen

# 4. Simular Falha 4 (queda do banco) e validar recuperação automática
docker stop cafeplanalto-dev-db
curl -i http://localhost:8088/health        # esperado: HTTP 503
docker start cafeplanalto-dev-db
curl -i http://localhost:8088/health        # esperado: volta para HTTP 200 sem reiniciar a API

# 5. Simular Falhas 5 e 6 (/admin/caos) e depois desligar
curl -s -X POST http://localhost:8088/admin/caos -H "Content-Type: application/json" -d '{"latencia_ms": 800, "taxa_erro": 0.2}'
curl -s -X POST "http://localhost:8088/admin/caos?latencia_ms=0&taxa_erro=0"
```

Para encerrar tudo (adicionando `-v` caso queira apagar os dados do banco):
```bash
docker compose down
```

## Testes automatizados da API (`pytest`)

```bash
# No Linux/WSL2:
python3 -m venv .venv && source .venv/bin/activate
pip install -r api/requirements.txt pytest httpx
pytest -v api/tests
```
