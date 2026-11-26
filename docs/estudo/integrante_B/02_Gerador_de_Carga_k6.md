# B2 — Gerador de Carga Contínua com `k6` (Integrante B)

Este módulo explica como funciona o nó **`cliente-carga`**, responsável por simular clientes comprando café na loja virtual a partir da Filial (**Requisito A3**).

> **Quer subir e testar na prática?** Siga o passo a passo completo em [`docs/Guia_Execucao_e_Testes.md`](../../Guia_Execucao_e_Testes.md).

---

## 1. Por que precisamos de Carga Contínua?

Sem tráfego chegando continuamente da Filial até a Matriz:
- Os gráficos de requisições por segundo, faturamento e latência `p95` no Grafana ficariam **zerados/vazios**.
- Falhas como **API lenta** (Falha 5) ou **20% de erro 500** (Falha 6) não gerariam amostras suficientes para disparar alertas automáticos no Prometheus/Alertmanager nem consumiriam o orçamento de erro (*Error Budget*).

O roteiro da disciplina pede tráfego contínuo de **5 a 20 requisições por segundo** com uma mistura de consultas e criação de pedidos.

---

## 2. O que é o `k6` e como ele está montado em `integrante_B/loadgen/`

**k6** (da Grafana Labs) é um gerador de carga leve em que escrevemos o comportamento dos clientes virtuais em JavaScript enquanto o motor em Go executa as requisições consumindo pouca RAM.

### 2.1 [`Dockerfile`](../../../integrante_B/loadgen/Dockerfile) (Multi-stage)
- Copia apenas o binário pronto do `k6` (`grafana/k6:0.54.0`) para dentro de um `alpine:3.20`.
- Instala também **`iproute2`**, `iputils` (`ping`), `traceroute`, `curl` e `bind-tools` (`dig`), permitindo que o mesmo contêiner na Filial (`172.20.20.20`) gere carga contínua e sirva para os testes de rede da apresentação.

### 2.2 [`script.js`](../../../integrante_B/loadgen/script.js)
- Usa o executor **`constant-arrival-rate`** configurado com `TARGET_RPS` (padrão `10 req/s`) para manter ritmo estável independentemente da lentidão da loja.
- Em cada iteração, sorteia uma ação realista:
  - **65%** `GET /produtos` (consulta ao catálogo)
  - **25%** `POST /pedidos` (compra com `produto_id` aleatório de 1 a 5 e quantidade de 1 a 3)
  - **5%** `GET /` (abertura da página inicial no Nginx)
  - **5%** `GET /health` (verificação de saúde)
- `discardResponseBodies: true`: descarta o corpo da resposta após ler o status HTTP para economizar memória RAM.

### 2.3 [`entrypoint.sh`](../../../integrante_B/loadgen/entrypoint.sh)
- Espera `STARTUP_DELAY` segundos para o Containerlab/Docker terminar de subir rotas e serviços.
- Roda o `k6` dentro de um loop infinito (`while true`) para garantir que o tráfego nunca pare sozinho durante uma demonstração longa.

---

## 3. Perguntas rápidas de arguição

1. **Por que o `cliente-carga` fica na LAN Filial (`172.20.20.20`) e não na LAN Serviços?**
   > Para obrigar todo o tráfego da loja a atravessar `r-filial`, o enlace WAN (`10.0.0.0/30`) e `r-matriz`. Se ele ficasse na mesma LAN da loja, uma queda na WAN não afetaria os clientes simulados.
2. **Qual a diferença entre `constant-arrival-rate` e um loop simples com `sleep`?**
   > Um loop simples com `sleep` reduz a taxa de requisições quando a API fica lenta (pois espera a resposta antes do próximo `sleep`). O `constant-arrival-rate` mantém o ritmo constante (ex.: `10 req/s`) ajustando o número de usuários virtuais (VUs) automaticamente.
