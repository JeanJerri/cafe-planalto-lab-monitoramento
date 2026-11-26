# B2 — Gerador de Carga Contínua com `k6` (Integrante B)

## 1. Por que isso existe?
Imagine abrir um painel de monitoramento de uma loja onde ninguém está entrando para comprar nada: todos os gráficos ficariam **zerados** e, se o professor desligasse o banco ou injetasse erro 500, ninguém veria o gráfico de erros subir!

Por isso o roteiro exige um robô chamado **`cliente-carga`** rodando na **Filial (`172.20.20.20`)**, simulando clientes reais navegando e comprando café o tempo todo (**5 a 20 requisições por segundo**).

---

## 2. Como funciona e onde está no projeto?

Usamos o **`k6`**, uma ferramenta leve da Grafana Labs que dispara requisições HTTP em paralelo usando pouquíssima memória RAM.

Os 3 arquivos ficam em [`integrante_B/loadgen/`](../../../integrante_B/loadgen/):
1. **[`Dockerfile`](../../../integrante_B/loadgen/Dockerfile):** junta o binário do `k6` com um Alpine Linux equipado com `iproute2`, `ping`, `traceroute`, `curl` e `dig` — assim o mesmo contêiner na Filial gera carga e serve para todos os testes de rede.
2. **[`script.js`](../../../integrante_B/loadgen/script.js):** define o comportamento do "cliente virtual" usando `constant-arrival-rate` (`TARGET_RPS = 10` req/s):
   - **65%** das vezes olha o catálogo (`GET /produtos`)
   - **25%** das vezes compra um café aleatório (`POST /pedidos`)
   - **5%** abre a página inicial (`GET /`) e **5%** checa `/health`
   - *Por que `constant-arrival-rate` e não um `sleep` simples?* Se a API ficar lenta (`800ms`), um loop com `sleep` reduziria os acessos por segundo; o `constant-arrival-rate` mantém a pressão constante de `10 req/s` abrindo mais conexões virtuais.
3. **[`entrypoint.sh`](../../../integrante_B/loadgen/entrypoint.sh):** espera `STARTUP_DELAY` segundos a rede subir e roda o `k6` dentro de um `while true` para nunca desligar sozinho.

---

## 3. Valide em 10 segundos + "E se eu tirasse isso?"

1. No terminal Ubuntu, rode:
   ```bash
   docker logs --tail 8 cafeplanalto-dev-loadgen
   ```
2. Abra `http://127.0.0.1:8088`, clique na aba **"Pedidos Recentes"** e depois clique 2 vezes em **"Atualizar lista"** após 3 segundos: você verá o total de pedidos e o faturamento subindo sozinhos com pedidos do cliente `filial-carga`!
3. **E se o `cliente-carga` ficasse na LAN Serviços em vez da Filial?** O tráfego não atravessaria o cabo WAN, então uma queda na WAN não interromperia as compras simuladas.

---

## 4. Pergunta rápida de arguição
* **O que muda nos gráficos se desligarmos o `cliente-carga`?**
  > A taxa de requisições (`rate(http_requests_total[1m])`) cai quase a zero (ficando apenas as sondas do Blackbox), os pedidos/min zeram e falhas na API (como `taxa_erro=0.2`) deixam de gerar erros visíveis porque não há clientes tentando comprar.
