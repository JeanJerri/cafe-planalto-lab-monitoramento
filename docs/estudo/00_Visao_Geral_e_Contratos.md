# 00 — Visão Geral, Contratos e a Regra de Ouro

Imagine que você não sabe nada de redes nem de monitoramento. Vamos começar olhando o "mapa da cidade" da empresa antes de entrar em qualquer código.

---

## 1. A História da Café Planalto (Por que esse trabalho existe?)

A **Café Planalto** vende cafés especiais pela internet em Vitória da Conquista (BA) e tem dois prédios ligados por uma conexão de longa distância (**WAN**):

```text
   PRÉDIO DA FILIAL                         CABO WAN                    PRÉDIO DA MATRIZ
  ┌──────────────────┐                    10.0.0.0/30               ┌────────────────────────┐
  │ • cliente-carga  │                   (.2)     (.1)              │ LAN Serviços (.10.x):  │
  │ • sonda Blackbox ├──[r-filial]════════════════════════[r-matriz]┤   dns, web, api, db    │
  │                  │                                              │ LAN Gerência (.99.x):  │
  └──────────────────┘                                              │   Zabbix, Prometheus,  │
   172.20.20.0/24                                                   │   Alertmanager, Grafana  │
                                                                    └────────────────────────┘
```

**O problema real:** no último mês, a loja caiu duas vezes (uma por problema no banco de dados e outra porque o cabo entre Filial e Matriz caiu) e ninguém da empresa percebeu antes dos clientes reclamarem.

**Nossa missão:** montar esse ambiente em miniatura dentro do computador (usando contêineres Docker leves) e colocar **dois sistemas de vigilância** olhando o **mesmo ambiente**:

| Ferramenta | Analogia | O que ela vigia melhor | Dono |
| --- | --- | --- | --- |
| **Zabbix** | **Médico do prédio e das estradas** | Roteadores (SNMP), cabos, se o servidor responde ping, CPU/disco, mapa da rede. | **Integrante A** |
| **Prometheus + Grafana + Loki** | **Médico da loja e dos clientes** | Quantos pedidos/seg entram, quantos dão erro 500, quanto tempo o cliente espera (`p95`), logs detalhados e metas de qualidade (SLOs). | **Integrante B (você)** |

---

## 2. Por que os IPs são fixos? (O "Contrato" da Dupla)

Pense em um condomínio onde o carteiro precisa entregar cartas todo dia. Se cada casa mudasse de número toda manhã, ninguém entregaria nada.
Como você faz a **loja e o Prometheus** (`integrante_B/`) e a Integrante A faz os **roteadores, DNS e Zabbix** (`integrante_A/`), o documento do professor trava os endereços para as duas metades se encaixarem sem conflito:

| Onde fica | Faixa de IP | Quem mora lá (e o número da casa) |
| --- | --- | --- |
| **Cabo WAN (entre prédios)** | `10.0.0.0/30` | `r-matriz` = `.1` · `r-filial` = `.2` |
| **LAN Serviços (Matriz)** | `172.20.10.0/24` | Roteador `.1` · `dns` `.10` · `web` (Nginx) `.20` · `api` `.21` · `db` (PostgreSQL) `.22` |
| **LAN Gerência (Matriz)** | `172.20.99.0/24` | Roteador `.1` · Zabbix `.10`–`.12` · Prometheus `.20` · Alertmanager `.21` · Grafana `.22` · Loki `.23` |
| **LAN Filial** | `172.20.20.0/24` | Roteador `.1` · `cliente-carga` `.20` · `sonda` (Blackbox) `.30` |
| **Porta dos fundos (`eth0`)** | `172.30.0.0/24` | Todos os contêineres têm — **só para administração/internet, NUNCA para tráfego da loja ou coleta!** |

---

## 3. A Regra de Ouro (`eth0` vs. `eth1`) — O erro que mais reprova

### 1) Por que isso existe?
Quando o Containerlab liga qualquer contêiner, o Docker coloca automaticamente uma placa **`eth0`** (`172.30.0.0/24`) ligando **todos** os contêineres direto entre si por fora da topologia — como uma "porta dos fundos" ou um corredor secreto onde não existem roteadores.

### 2) O que acontece se o monitoramento ou a loja usarem a `eth0`?
Imagine que o professor quer testar a **Falha 1**: ele corta o cabo WAN entre Filial e Matriz.
- Se os pedidos da Filial e as medições passarem pela **`eth1`** (o caminho real), eles passam por `r-filial` → cabo WAN → `r-matriz`. Quando o cabo WAN cai, **tudo para e os alarmes disparam** (correto!).
- Se alguém errar as rotas e deixar o tráfego escapar pela **`eth0`**, os pacotes dão a volta por fora do cabo WAN — e **nenhum alarme dispara**! O cenário de falha inteiro perde o sentido.

### 3) Onde isso está no projeto?
- Em [`integrante_A/infra/topology.yml`](../../integrante_A/infra/topology.yml): cada servidor recebe rotas explícitas mandando `172.20.0.0/16` e `10.0.0.0/30` pela `eth1` rumo ao gateway `.1`.
- Em [`integrante_B/observability/prometheus/prometheus.clab.yml`](../../integrante_B/observability/prometheus/prometheus.clab.yml): todos os alvos usam IPs `172.20.x.x` e `10.0.0.x` (existe até um teste automático no `pytest` que falha se alguém escrever `172.30.0.` lá dentro!).

### 4) Como você prova isso na prática (10 segundos)
No Containerlab, você derruba a WAN (`ip link set eth1 down` no `r-filial`) e tenta pingar `172.20.10.21` a partir da Filial: **tem que dar 100% de perda**. Se responder, significa que vazou pela `eth0`!

---

## 4. Por que cuidamos de WSL2 e Linux ao mesmo tempo?

Você e a Integrante A usam **Windows + WSL2** (um Linux Ubuntu real rodando dentro do Windows), e mantemos compatibilidade com Linux nativo/VM Ubuntu caso apresentem em outro computador:
- **Quebra de linha `LF` (`.gitattributes`):** scripts Linux quebram com erro invisível se forem salvos com `\r\n` do Windows. O `.gitattributes` na raiz impede isso automaticamente.
- **Rodar em `~/Projeto_Final` (não em `/mnt/c/...`):** no WSL2, `/mnt/c/` passa por uma tradução lenta do Windows que atrapalha bancos de dados.
- **Portas sem briga (`8080` vs. `8088`/`8085`):** o Zabbix usa a porta `8080` no navegador; por isso colocamos a loja em `8088` e o `cAdvisor` em `8085` nos testes locais.
- **Falha 3 (`tc netem`):** já testamos no WSL2 que seu kernel (`6.6.87.2`) aceita `tc qdisc ... netem` normalmente!
