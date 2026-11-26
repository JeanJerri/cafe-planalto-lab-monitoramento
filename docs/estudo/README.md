# Trilha de Estudos — Café Planalto (Monitoramento e Observabilidade)

Esta pasta organiza o conteúdo do trabalho prático em **módulos curtos e progressivos para quem está começando do zero**. Cada guia explica **o que é**, **por que existe**, **como funciona nos arquivos reais do repositório** e **como responder na arguição individual cruzada**.

> **Regra de ouro da avaliação:** na apresentação, o professor faz perguntas individuais sobre **a parte que você NÃO apresentou**. Por isso, estude tanto a trilha do **Integrante B** quanto a do **Integrante A**.

---

## Ordem Recomendada de Leitura

### Base Comum (para os dois integrantes)
1. [**00 — Visão Geral, Contratos e Linux vs. WSL2**](00_Visao_Geral_e_Contratos.md)
   - A história da Café Planalto, plano completo de IPs e portas, `eth0` vs. `eth1`, divisão de pastas e cuidados entre Linux nativo (Integrante A) e WSL2 (Integrante B).

### Trilha do Integrante A — Infraestrutura, Rede e Zabbix
2. [**A1 — Redes, Topologia Containerlab e Roteamento Estático**](integrante_A/01_Redes_Topologia_e_Roteamento.md)
   - Interfaces (`eth0`, `eth1`, `eth2`), MAC vs. IP, CIDR (`/30`, `/24`, `/16`), gateway, bridge (Camada 2) vs. roteador (Camada 3), `ip_forward=1`, *Longest Prefix Match*, `ping`/`TTL`/`traceroute` e análise do `topology.yml`.
3. [**A2 — DNS (CoreDNS), SNMP v2c e Base do Zabbix**](integrante_A/02_DNS_SNMP_e_Zabbix_Base.md)
   - Resolução de nomes (`cafeplanalto.lab`, `loja.cafeplanalto.lab`), `snmpd` na Matriz e Filial, OIDs/communities, arquitetura dos contêineres do Zabbix 8.0 LTS e o que ainda falta a Integrante A concluir.

### Trilha do Integrante B — Aplicação, Carga e Observabilidade Moderna
4. [**B1 — Aplicação em 3 Camadas (Nginx + FastAPI + PostgreSQL)**](integrante_B/01_Aplicacao_3_Camadas_Nginx_API_DB.md)
   - HTTP/REST/JSON, Docker (`Dockerfile`, `iproute2`), Nginx como proxy reverso + `stub_status`, API FastAPI, métricas Prometheus (Counter, Histogram, p95, Gauge, cardinalidade), logs JSON, `/admin/caos`, `/health` e resiliência com PostgreSQL.
5. [**B2 — Gerador de Carga Contínua (`k6`) e Testes Locais**](integrante_B/02_Gerador_de_Carga_e_Testes_Locais.md)
   - Como funciona o `k6` simulando clientes comprando café continuamente (`5–20 req/s`) e passo a passo prático para subir tudo com `docker compose`, testar no navegador/`curl` e simular as falhas 4, 5 e 6 localmente no WSL2.

*(Os módulos `B3` a `B5` — Exporters/Prometheus/Alertmanager, Loki, Dashboards Grafana/SLOs — e `06 — Ensaios de Caos e Arguição` serão adicionados nas próximas fases.)*

---

## Mapa de Requisitos do Barema (100 pontos)

| Bloco | Pontos | Responsável | Onde está no repositório |
| --- | --- | --- | --- |
| **I. Infraestrutura (I1–I4)** | 15 pts | Integrante A (com contratos comuns) | `integrante_A/infra/`, `integrante_A/dns/` |
| **A. Aplicação (A1–A3)** | 10 pts | **Integrante B** | `integrante_B/{web,api,db,loadgen}/` |
| **Z. Zabbix (Z1–Z8)** | 25 pts | Integrante A | `integrante_A/zabbix/`, `integrante_A/snmp/` |
| **P. Prometheus + Grafana (P1–P4)** | 20 pts | **Integrante B** | *Fases 2 e 3 em `integrante_B/`* |
| **O. Observabilidade / Loki / SLOs (O1–O3)** | 10 pts | **Integrante B** | *Fase 3 em `integrante_B/`* |
| **Falhas ao vivo (2 sorteadas)** | 12 pts | **Ambos (juntos)** | *Fase 5* |
| **Relatório comparativo e README** | 8 pts | **Ambos (tópicos invertidos)** | `README.md` e relatório PDF final |
