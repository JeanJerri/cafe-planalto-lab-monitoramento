# Trilha de Estudos — Café Planalto (Do Zero à Prática)

Estes guias foram feitos para quem está **começando do zero em redes e programação**. Em vez de jogar termos soltos ou listas gigantes de comandos, **cada assunto segue sempre a mesma lógica em 4 passos**:

1. **Por que isso existe?** — o problema real do mundo físico/empresa que aquela peça resolve (com analogia simples).
2. **Como funciona?** — o caminho passo a passo sem pular etapas.
3. **Onde está no nosso projeto?** — o arquivo exato e a linha onde aquilo mora no código.
4. **Valide em 10 segundos + "E se eu tirasse isso?"** — um teste rápido para você ver funcionando com os próprios olhos e entender o que quebra se aquilo falhar.

> **Quer subir tudo do começo ao fim no WSL2?** Use o manual operacional separado: [`docs/Guia_Execucao_e_Testes.md`](../Guia_Execucao_e_Testes.md).
>
> **Regra da avaliação:** na apresentação, o professor faz perguntas individuais sobre **a parte que você NÃO apresentou**. Estude as duas trilhas!

---

## Ordem Recomendada de Leitura

### Base Comum (para entender o mapa todo)
1. [**00 — Visão Geral, Contratos e Regra de Ouro**](00_Visao_Geral_e_Contratos.md)
   - O mapa da Café Planalto, por que temos duas ferramentas de monitoramento e a lógica dos IPs + `eth0` vs. `eth1`.

### Trilha do Integrante A — A Estrada por Onde os Dados Passam
2. [**A1 — Redes, Topologia Containerlab e Roteamento Estático**](integrante_A/01_Redes_Topologia_e_Roteamento.md)
   - Acompanhe a viagem de um pacote saindo da Filial até a Matriz: placas `eth0`/`eth1`, MAC vs. IP, CIDR (`/30`, `/24`, `/16`), gateway, switch vs. roteador, `ip_forward=1`, rotas estáticas e `traceroute`.
3. [**A2 — DNS (CoreDNS), SNMP v2c e Zabbix**](integrante_A/02_DNS_SNMP_e_Zabbix_Base.md)
   - Como nomes viram IPs (`loja.cafeplanalto.lab`), como o Zabbix lê os roteadores pela WAN usando SNMP + descoberta automática (LLD) e o papel de cada contêiner do Zabbix.

### Trilha do Integrante B — A Loja e os Sensores Modernos
4. [**B1 — Aplicação em 3 Camadas: Nginx, API FastAPI e PostgreSQL**](integrante_B/01_Aplicacao_3_Camadas_Nginx_API_DB.md)
   - Acompanhe **1 clique no botão "Fazer Pedido"** na loja: HTTP, JSON, Docker (`iproute2`), Nginx (proxy reverso + `stub_status`), API FastAPI, PostgreSQL (pool resiliente), métricas Prometheus, cardinalidade, logs JSON e `/admin/caos`.
5. [**B2 — Gerador de Carga Contínua (`k6`)**](integrante_B/02_Gerador_de_Carga_k6.md)
   - Por que um robô precisa comprar café sem parar pela Filial e como ele funciona dentro do `loadgen/`.
6. [**B3 — Exporters, Sonda Blackbox, Prometheus e Alertmanager (E-mail)**](integrante_B/03_Exporters_Blackbox_Prometheus_Alertmanager.md)
   - Como os "tradutores" (exporters) expõem números, como a sonda da Filial testa a loja "por fora", como o Prometheus lê tudo (`Pull` + PromQL) e como o Alertmanager envia `[FIRING]` e `[RESOLVED]` para o seu celular.

*(Os módulos `B4` e `B5` — Logs no Loki + Dashboards Grafana e SLOs — entram na Fase 3.)*

---

## Mapa de Pontuação do Trabalho (100 pontos)

| Bloco | Pontos | Dono | Onde mora no repositório |
| --- | --- | --- | --- |
| **I. Infraestrutura (I1–I4)** | 15 pts | Integrante A | `integrante_A/infra/`, `integrante_A/dns/` |
| **A. Aplicação (A1–A3)** | 10 pts | **Integrante B** | `integrante_B/{web,api,db,loadgen}/` |
| **Z. Zabbix (Z1–Z8)** | 25 pts | Integrante A | `integrante_A/zabbix/`, `integrante_A/snmp/` |
| **P. Prometheus + Grafana (P1–P4)** | 20 pts | **Integrante B** | `integrante_B/observability/` *(P4 na Fase 3)* |
| **O. Observabilidade / Loki / SLOs (O1–O3)** | 10 pts | **Integrante B** | *Fase 3* |
| **Falhas ao vivo (2 sorteadas)** | 12 pts | **Ambos** | Ensaios locais agora; integrados na Fase 5 |
| **Relatório comparativo e README** | 8 pts | **Ambos (invertido)** | Consolidação final |
