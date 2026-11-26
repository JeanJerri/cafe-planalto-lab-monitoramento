# B2 — Gerador de Carga Contínua (`k6`) e Testes Locais no WSL2 (Integrante B)

Sem tráfego contínuo chegando da filial até a matriz, os gráficos do Grafana ficam vazios e as falhas simuladas não aparecem nos painéis. Este módulo explica como funciona o **`cliente-carga`** (`k6`) e mostra o passo a passo exato para rodar e testar toda a aplicação no seu **WSL2 / Docker**.

---

## 1. Como Funciona o `cliente-carga` (`integrante_B/loadgen/`)

### 1.1 O que é o `k6`?
**k6** (da Grafana Labs) é uma ferramenta moderna de teste de carga em que escrevemos o comportamento dos clientes virtuais em JavaScript ([`script.js`](../../integrante_B/loadgen/script.js)) enquanto o motor em Go executa milhares de requisições leves com baixíssimo consumo de RAM.

### 1.2 Entendendo cada arquivo em `integrante_B/loadgen/`
1. **[`Dockerfile`](../../integrante_B/loadgen/Dockerfile) (Multi-stage):**
   - Copia apenas o binário pronto do `k6` (`grafana/k6:0.54.0`) para dentro de um `alpine:3.20` equipado com **`iproute2`**, `iputils` (`ping`), `traceroute`, `curl` e `bind-tools` (`dig`).
   - Assim, o mesmo contêiner gera carga contínua **e** permite rodar todos os comandos de verificação do professor (`dig`, `traceroute`, `curl`) a partir da Filial!
2. **[`script.js`](../../integrante_B/loadgen/script.js):**
   - Usa o executor `constant-arrival-rate` configurado com `TARGET_RPS` (padrão `10` req/s — dentro da faixa de `5` a `20` req/s pedida no roteiro).
   - Em cada requisição, sorteia uma ação realista:
     - **65%** `GET /produtos` (clientes olhando o catálogo)
     - **25%** `POST /pedidos` (clientes comprando cafés aleatórios de ID `1` a `5`, quantidade `1` a `3`)
     - **5%** `GET /` (abertura da página inicial no Nginx)
     - **5%** `GET /health` (verificação de saúde)
   - `discardResponseBodies: true`: descarta o corpo da resposta após ler o status HTTP para economizar memória RAM.
3. **[`entrypoint.sh`](../../integrante_B/loadgen/entrypoint.sh):**
   - Aguarda `STARTUP_DELAY` segundos para o Containerlab/Docker terminar de configurar placas e rotas.
   - Executa o `k6` dentro de um loop infinito (`while true`): se o teste terminar após 24h ou cair por qualquer motivo, ele reinicia automaticamente em 2 segundos.

---

## 2. Passo a Passo Prático no WSL2 (Teste Local Isolado)

Você ainda não precisa ter o Containerlab rodando para validar 100% da aplicação 3 camadas e da carga contínua. O arquivo [`integrante_B/docker-compose.yml`](../../integrante_B/docker-compose.yml) sobe `db`, `api`, `web` e `cliente-carga` juntos no Docker.

### Passo 2.1 — Abrir o terminal Ubuntu (WSL2) e ir para a pasta correta
> **Importante:** no WSL2, prefira manter sua cópia de trabalho dentro da home Linux (`~/Projeto_Final`) em vez de `/mnt/c/...`, para evitar lentidão e problemas de permissão no PostgreSQL.

Se você ainda está acessando pelo `/mnt/c/...`, pode sincronizar para `~/Projeto_Final` ou entrar direto na pasta onde clonou:
```bash
# Verifique se o Docker está ativo
docker --version
docker compose version

# Entre na pasta do Integrante B (ajuste o caminho se clonou em ~/Projeto_Final)
cd ~/Projeto_Final/integrante_B
```

### Passo 2.2 — Subir as 3 camadas + gerador de carga
```bash
docker compose up -d --build
```
Aguarde o build terminar e confira se todos os 4 contêineres estão `Up` (e `db` como `healthy`):
```bash
docker compose ps
```

### Passo 2.3 — Testar no Navegador e no Terminal
No navegador do Windows (o WSL2 encaminha `localhost` automaticamente), abra:
- **`http://localhost:8088`** → Loja Café Planalto (carrega os 5 cafés e permite clicar em **"Comprar 1 unidade"**).
- **`http://localhost:8089/nginx_status`** → Contadores internos (`stub_status`) do Nginx.
- **`http://localhost:8000/docs`** → Documentação interativa Swagger da API.
- **`http://localhost:8000/metrics`** → Métricas Prometheus subindo sozinhas por causa do `k6`!

No terminal Ubuntu, confira o tráfego e os logs JSON ao vivo:
```bash
# 1. Conferir saúde pelo Nginx (esperado: HTTP/1.1 200 OK e {"status":"ok","database":"postgres"})
curl -i http://localhost:8088/health

# 2. Conferir métricas de negócio crescendo (pedidos_criados_total e pedidos_valor_reais_total)
curl -s http://localhost:8000/metrics | grep -E "pedidos_|db_pool|http_requests_total"

# 3. Ver os últimos logs JSON do Nginx (web) e da API (api)
docker logs --tail 5 cafeplanalto-dev-web
docker logs --tail 5 cafeplanalto-dev-api

# 4. Ver o gerador de carga rodando
docker logs --tail 10 cafeplanalto-dev-loadgen
```

---

## 3. Ensaio Local das Falhas 4, 5 e 6 (Antes do Containerlab)

### Falha 4 — Banco de dados parado (`docker stop`)
```bash
# Derruba apenas o PostgreSQL
docker stop cafeplanalto-dev-db

# /health imediatamente retorna 503 Service Unavailable
curl -i http://localhost:8088/health

# Logs da API passam a mostrar nivel ERROR e status 503
docker logs --tail 5 cafeplanalto-dev-api

# Religa o banco e confirma que a API e a carga se recuperam sozinhas sem reiniciar!
docker start cafeplanalto-dev-db
sleep 3
curl -i http://localhost:8088/health
```

### Falhas 5 e 6 — Latência artificial e Erros 500 (`/admin/caos`)
```bash
# Injetar 800ms de lentidão e 20% de erro HTTP 500
curl -s -X POST http://localhost:8088/admin/caos \
  -H "Content-Type: application/json" \
  -d '{"latencia_ms": 800, "taxa_erro": 0.2}'

# Testar /produtos (vai demorar ~0.8s e algumas darão 500)
curl -i http://localhost:8088/produtos

# Conferir que /health continua 200 OK (provando que o banco está saudável e o defeito é na API)
curl -i http://localhost:8088/health

# Desligar o caos
curl -s -X POST "http://localhost:8088/admin/caos?latencia_ms=0&taxa_erro=0"
```

### Encerrar o ambiente local quando terminar
```bash
docker compose down
```
*(Use `docker compose down -v` apenas se quiser apagar os dados gravados no volume do PostgreSQL.)*

---

## 4. Rodando os Testes Automatizados (`pytest`)

Os testes unitários da API rodam em memória (inclusive simulando falhas e recuperação do PostgreSQL sem depender do Docker):
```bash
# No Linux/WSL2 (dentro de integrante_B/):
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt pytest httpx
pytest -v api/tests
```
Esperado: **`7 passed`**.
