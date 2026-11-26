# A2 — DNS (CoreDNS), SNMP v2c e Base do Zabbix (Integrante A)

Este módulo explica os serviços de rede e monitoramento tradicional iniciados pela Integrante A na Semana 2 (`dns/`, `snmp/` e `zabbix/`), para que você consiga explicá-los na arguição cruzada.

---

## 1. DNS Interno com CoreDNS (`integrante_A/dns/Corefile`)

### 1.1 Para que serve o DNS?
Sem DNS, precisaríamos decorar IPs como `http://172.20.10.20`. O **DNS (*Domain Name System*)** funciona como uma agenda telefônica que traduz nomes fáceis (`loja.cafeplanalto.lab`) para IPs (`172.20.10.20`), usando a **porta `53` (UDP/TCP)**.

### 1.2 Como o CoreDNS está configurado
Em [`integrante_A/infra/Dockerfile.dns`](../../integrante_A/infra/Dockerfile.dns), a imagem usa Alpine + `coredns` + `bind-tools` (que traz o comando `dig` usado pelo professor no Barema I2).

O arquivo [`integrante_A/dns/Corefile`](../../integrante_A/dns/Corefile) define a zona autoritativa **`cafeplanalto.lab`** na porta `53`:
- `loja.cafeplanalto.lab` e `web.cafeplanalto.lab` → `172.20.10.20` (proxy reverso Nginx)
- `api.cafeplanalto.lab` → `172.20.10.21`
- `db.cafeplanalto.lab` → `172.20.10.22`
- `dns.cafeplanalto.lab` → `172.20.10.10`
- Todos os nós da LAN Gerência (`172.20.99.x`) e LAN Filial (`172.20.20.x`) + roteadores.

> **Correção pontual feita na Fase 1:** originalmente a Integrante A havia testado o domínio `cafeplanalto.test` no IP `172.20.10.53`. Corrigimos para `cafeplanalto.lab` no IP **`172.20.10.10`** com `loja.cafeplanalto.lab -> 172.20.10.20` para cumprir rigorosamente o contrato do PDF oficial.

### 1.3 Como testar (Requisito I2)
```bash
dig @172.20.10.10 loja.cafeplanalto.lab +short
# Esperado: 172.20.10.20
```
*(E com `/etc/resolv.conf` configurado nos nós apontando para `nameserver 172.20.10.10`, basta digitar `dig loja.cafeplanalto.lab`.)*

---

## 2. SNMP v2c nos Roteadores (`integrante_A/snmp/`)

### 2.1 O que é SNMP?
**SNMP (*Simple Network Management Protocol*)** é o protocolo padrão da indústria para monitorar roteadores, switches e ativos de rede, operando na **porta UDP `161`**.
- **Agente (`snmpd`):** roda dentro de `r-matriz` e `r-filial`, expondo contadores do kernel Linux (bytes trafegados por placa, pacotes descartados, erros, status `UP/DOWN`).
- **Gerente (Zabbix Server):** envia consultas periódicas (`GET` / `WALK`) para o `snmpd` usando uma senha compartilhada chamada **community** (`rocommunity`, modo somente leitura).
- **OID e MIB:** cada dado no SNMP tem um endereço numérico hierárquico chamado **OID** (ex.: `ifOperStatus` indica se `eth1` está `up(1)` ou `down(2)`), organizado em tabelas chamadas **MIBs**.

### 2.2 O que a Integrante A configurou nos roteadores
Em `integrante_A/infra/Dockerfile`, ela instalou `net-snmp` e `net-snmp-tools` e subiu o `snmpd` em `r-matriz` e `r-filial`.
Observe o detalhe importante de segurança e roteamento:
- No `r-matriz`, o `snmpd` escuta no IP da LAN Gerência (`172.20.99.1:161`) e aceita consultas apenas de `172.20.99.0/24`.
- No `r-filial`, o `snmpd` escuta no IP da **WAN (`10.0.0.2:161`)** aceitando consultas vindas de `172.20.99.0/24` (onde fica o Zabbix Server `172.20.99.10`).
- **Por que `10.0.0.2` e não `eth0`?** Para obedecer à Regra de Ouro: o Zabbix consulta o `r-filial` atravessando o `r-matriz` e a WAN!
- **Segurança:** a *community* real fica em `snmp/.community` e `snmp/snmpd-*.conf` (ignorados no `.gitignore` para não vazar senhas no GitHub).

### 2.3 O que é LLD (*Low-Level Discovery*) no Zabbix?
Em vez de cadastrar manualmente `eth0`, `eth1`, `eth2`, `eth3` uma por uma, o template [`template_net_generic_snmp.yaml`](../../integrante_A/zabbix/templates/template_net_generic_snmp.yaml) usa **LLD (Descoberta de Baixo Nível)**: o Zabbix consulta a tabela de interfaces (`IF-MIB`) do roteador e cria automaticamente os itens, gráficos e triggers de tráfego, erros e estado operacional de cada placa encontrada.

---

## 3. A Pilha do Zabbix (`integrante_A/zabbix/docker-compose.yml`)

A Integrante A subiu os 3 serviços base do **Zabbix 8.0 LTS** na faixa `172.20.99.10-12`:
1. **`postgres-server` (`172.20.99.12`):** banco PostgreSQL 17 que guarda toda a configuração do Zabbix (hosts, templates, triggers) e o histórico das coletas.
2. **`zabbix-server` (`172.20.99.10`):** o "cérebro" que dispara coletas SNMP/Agent/ICMP (porta `10051`) e avalia triggers.
3. **`zabbix-web` (`172.20.99.11`):** interface web em Nginx+PHP exposta localmente na porta `8080` (`http://127.0.0.1:8080`).

### O que ainda pertence à Integrante A concluir
*(Nota informativa — faz parte do escopo dela, não alteraremos sem necessidade):*
- Conectar a pilha Zabbix diretamente à `sw-gerencia` do Containerlab (ou bridge correspondente) sem vazar por `eth0`.
- Instalar/configurar Zabbix Agent 2 nos servidores da matriz (`dns`, `web`, `api`, `db`) com templates Linux, Nginx e PostgreSQL (Requisito Z2).
- Configurar verificações ICMP da WAN e filial (Z4), cenário web de 2 passos (Z5), triggers com dependências anti-cascata (Z6), mapa de rede (Z7) e canal real de notificação (Z8).

---

## 4. Simulado de Arguição (Perguntas da Parte A)

1. **Qual a diferença entre Zabbix Agent (passivo/ativo) e SNMP?**
   > O Zabbix Agent é um software instalado dentro do servidor (Linux, Nginx, PostgreSQL) com acesso profundo a processos e arquivos locais. O SNMP é um protocolo leve nativo em roteadores e switches onde não é possível instalar agentes tradicionais.
2. **Para que serve a dependência de triggers no Zabbix (Requisito Z6)?**
   > Se o roteador `r-filial` cai, os hosts atrás dele (`cliente-carga`, `sonda`) ficam inalcançáveis como consequência. Com dependência configurada, o Zabbix suprime os alertas dos hosts da filial e exibe apenas 1 problema raiz (`r-filial` fora), evitando tempestade de alertas (*alert storm*).
3. **O que significa `LLD` no monitoramento SNMP?**
   > *Low-Level Discovery*: descoberta automática das interfaces (`eth1`, `eth2`...) de um roteador via SNMP para gerar itens de tráfego, erros e status sem precisar criá-los manualmente.
