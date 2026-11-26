# 00 — Visão Geral, Contratos do Ambiente e Linux × WSL2

Este capítulo apresenta o cenário completo da empresa **Café Planalto**, os endereços combinados entre a dupla e os cuidados para trabalhar em conjunto quando uma pessoa usa **Linux nativo (Integrante A)** e a outra usa **Windows + WSL2 (Integrante B)**.

---

## 1. A História do Problema (O Desafio)

A **Café Planalto** é uma torrefação fictícia de Vitória da Conquista (BA) que vende cafés especiais pela internet. A empresa possui duas unidades ligadas por um enlace de longa distância (**WAN**):
- **Matriz:** hospeda o site/loja virtual, os servidores de DNS/banco e as duas plataformas de monitoramento.
- **Filial:** unidade remota com atendentes e ferramentas que testam a loja **atravessando a WAN** (como clientes reais).

No último mês, a loja caiu duas vezes (uma por falha no banco de dados e outra por queda da WAN) e a diretoria só soube pelos clientes. A missão da dupla é construir o laboratório virtual reproduzível e implantar **duas abordagens de monitoramento sobre o mesmo ambiente**:
1. **Zabbix (Integrante A):** foco tradicional em rede e infraestrutura (roteadores via SNMP, ICMP, agentes Linux/Nginx/PostgreSQL, mapa e dependências de triggers).
2. **Prometheus + Alertmanager + Grafana + Loki (Integrante B):** foco moderno em aplicação, contêineres, métricas de serviço, logs estruturados, sondas remotas e SLOs.

---

## 2. Plano de Endereçamento Oficial (O "Contrato" da Dupla)

Para que os arquivos da Integrante A e do Integrante B se encaixem sem conflito, os IPs do roteiro são fixos:

| Segmento | Rede CIDR | Nós e IPs exatos |
| --- | --- | --- |
| **WAN Matriz ↔ Filial** | `10.0.0.0/30` | `r-matriz` = `.1` · `r-filial` = `.2` |
| **LAN Serviços (Matriz)** | `172.20.10.0/24` | Gateway = `.1` · `dns` = `.10` · `web` (Nginx) = `.20` · `api` (FastAPI) = `.21` · `db` (PostgreSQL) = `.22` |
| **LAN Gerência (Matriz)** | `172.20.99.0/24` | Gateway = `.1` · `zabbix-server` = `.10` · `zabbix-web` = `.11` · `zabbix-db` = `.12` · `prometheus` = `.20` · `alertmanager` = `.21` · `grafana` = `.22` · `loki` = `.23` · *(apoio da A: `host-gerencia` = `.100`)* |
| **LAN Filial** | `172.20.20.0/24` | Gateway = `.1` · `cliente-carga` = `.20` · `sonda` (Blackbox Exporter) = `.30` |
| **Gerência Fora de Banda** | `172.30.0.0/24` | `eth0` de todos os nós — **exclusiva para administração e internet, NUNCA para coleta!** |

### A Regra de Ouro (`eth0` vs. `eth1`)
Quando o Containerlab cria qualquer contêiner, ele coloca uma interface `eth0` ligada na rede `172.30.0.0/24` (`clab-mgmt`) com uma rota padrão (`default`) para a internet.
- Se uma ferramenta de monitoramento ou o gerador de carga enviar pacotes usando a `eth0`, o tráfego **dá um atalho fora da topologia** e **não atravessa os roteadores nem a WAN**.
- Consequência: quando o professor derrubar o cabo WAN (`ip link set eth1 down`), o monitoramento continuaria enxergando tudo normal — **e o cenário de falha perderia o sentido**.
- Por isso, todos os nós recebem rotas explícitas para `172.20.0.0/16` e `10.0.0.0/30` apontando para o gateway `.1` da própria LAN (via `eth1`).

---

## 3. Organização de Pastas no Repositório

```text
Projeto_Final/
├── .gitignore            # Bloqueia .env, .venv/, snmp/.community, clab-cafeplanalto/, .agente/
├── .gitattributes        # Força fim de linha LF em scripts, YAML, conf e Dockerfiles
├── docs/                 # PDF oficial, Divisao.md e trilha de estudos (docs/estudo/)
├── integrante_A/         # Infraestrutura de rede (Containerlab), DNS, SNMP e Zabbix
└── integrante_B/         # Aplicação 3 camadas (web, api, db), carga k6 e observabilidade
```

---

## 4. Cuidados Essenciais: Linux Nativo (Integrante A) × WSL2 (Integrante B)

Como a Integrante A desenvolve direto no Linux e você usa Windows + **WSL2** (um kernel Linux real rodando dentro do Windows), alguns detalhes práticos evitam bugs invisíveis:

1. **Fim de linha (`LF` vs `CRLF`):**
   - Windows costuma salvar textos com `\r\n` (`CRLF`), enquanto Linux e shells `#!/bin/sh` exigem `\n` (`LF`). Um script `.sh` com `CRLF` falha com `not found` ao rodar dentro de um contêiner Alpine.
   - **Solução aplicada:** o arquivo `.gitattributes` na raiz força `eol=lf` em todos os `.sh`, `.yml`, `.conf`, `.py`, `Dockerfile*` e `Corefile`.
2. **Onde rodar Docker/Containerlab no WSL2 (`~/...` vs `/mnt/c/...`):**
   - O disco do Windows aparece no Ubuntu WSL2 em `/mnt/c/...`, que passa por uma ponte de sistema de arquivos mais lenta e com permissões diferentes para bancos de dados (PostgreSQL/Prometheus/Loki).
   - **Boa prática:** para rodar o laboratório no WSL2, clone ou copie o projeto dentro da sua pasta Linux nativa (`~/Projeto_Final`) e use **volumes nomeados** do Docker para persistência.
3. **Sincronização de relógio no WSL2:**
   - Métricas e logs dependem do horário exato para aparecerem alinhados no Grafana. Às vezes, quando o notebook hiberna no Windows, o relógio do WSL2 atrasa.
   - Se notar horários estranhos nos logs, rode no terminal Ubuntu WSL2:
     ```bash
     sudo hwclock -s
     ```
4. **Conflito de portas locais (`8080`):**
   - O `zabbix-web` da Integrante A usa a porta local `8080`. Por isso, no `docker-compose.yml` de testes do Integrante B usamos **`8088`** para a loja (`web`) e **`8089`** para o `stub_status` do Nginx.
5. **Particularidades do kernel WSL2 (`cAdvisor` e `tc netem`):**
   - No WSL2, o `cAdvisor` precisa de flags específicas para não tentar ler `/dev/disk` inexistente (trataremos isso na Fase 2).
   - Na Falha 3 (`tc qdisc add dev eth1 root netem delay 300ms loss 5%`), o kernel padrão de algumas versões do WSL2 não vem com o módulo `sch_netem` compilado, enquanto no Linux nativo da Integrante A funciona normalmente. Testaremos isso antes da apresentação!
