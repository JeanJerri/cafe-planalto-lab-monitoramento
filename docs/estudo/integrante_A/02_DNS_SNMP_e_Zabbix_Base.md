# A2 — DNS (CoreDNS), SNMP v2c e Zabbix (Integrante A)

Aqui você aprende as 3 peças de serviço e monitoramento que ficam do lado da **Integrante A**: como nomes viram IPs, como roteadores respondem ao monitoramento e como o Zabbix funciona.

---

## 1. DNS Interno com CoreDNS (`cafeplanalto.lab`)

### 1) Por que isso existe?
Ninguém lembra se a loja fica no IP `172.20.10.20` ou `.21`. O **DNS (*Domain Name System*)** é a **agenda telefônica da rede** (porta **`53`**): você pergunta *"qual é o número de `loja.cafeplanalto.lab`?"* e ele responde `172.20.10.20`.

### 2) Onde está no projeto?
Em [`integrante_A/dns/Corefile`](../../integrante_A/dns/Corefile), o CoreDNS (nó `dns` no IP `172.20.10.10`) guarda o mapa de nomes de toda a empresa:
- `loja.cafeplanalto.lab` → `172.20.10.20` (`web` Nginx)
- `api.cafeplanalto.lab` → `172.20.10.21`
- `db.cafeplanalto.lab` → `172.20.10.22`

### 3) Valide em 10 segundos + "E se eu tirasse isso?"
```bash
sudo docker exec clab-cafeplanalto-dns dig @172.20.10.10 loja.cafeplanalto.lab +short
# Saída esperada: 172.20.10.20
```
**Se o contêiner `dns` parar (Falha 7):** o IP `172.20.10.20` até continua vivo, mas ninguém consegue abrir a loja pelo nome `loja.cafeplanalto.lab` — e tanto a sonda DNS do Prometheus quanto o item `net.dns` do Zabbix disparam alerta.

---

## 2. SNMP v2c e Descoberta Automática (`LLD`)

### 1) Por que isso existe?
Em servidores Linux comuns (como `web`, `api`, `db`), podemos instalar programas pesados para monitorar CPU e disco. Já em **roteadores e switches**, normalmente não se instala um agente completo: eles já trazem um protocolo leve e universal chamado **SNMP** (porta **UDP `161`**).

### 2) Como funciona (3 palavras-chave fáceis)?
- **`snmpd` (o agente no roteador):** fica ouvindo na porta UDP `161` e responde perguntas como *"quantos bytes passaram pela `eth1`?"* ou *"a `eth1` está ligada ou desligada?"*.
- **`community`:** é a "senha de leitura" compartilhada entre o Zabbix e o roteador (ex.: `rocommunity <senha> 172.20.99.0/24`).
- **`LLD` (*Low-Level Discovery*):** em vez de a Integrante A cadastrar manualmente `eth1`, `eth2`, `eth3` no Zabbix, o LLD faz uma varredura automática no roteador e descobre todas as placas de rede sozinho, criando gráficos de tráfego, erros e estado (`UP`/`DOWN`).

### 3) Onde está no nosso projeto?
- Em `integrante_A/snmp/snmpd-matriz.conf`: o `r-matriz` escuta em **`172.20.99.1:161`** (LAN Gerência).
- Em `integrante_A/snmp/snmpd-filial.conf`: o `r-filial` escuta em **`10.0.0.2:161`** (ponta da **WAN**!).
  - **Por que `10.0.0.2`?** Para obedecer à Regra de Ouro: o Zabbix (`172.20.99.10`) consulta o `r-filial` atravessando o `r-matriz` e o cabo WAN.
- Em [`integrante_A/zabbix/templates/template_net_generic_snmp.yaml`](../../integrante_A/zabbix/templates/template_net_generic_snmp.yaml): template exportado com as regras de LLD.

### 4) Valide em 10 segundos + "E se a WAN cair?"
```bash
COMMUNITY=$(cat integrante_A/snmp/.community)
sudo docker exec clab-cafeplanalto-host-gerencia snmpwalk -v2c -c "$COMMUNITY" 10.0.0.2 system
```
Quando derrubamos a `eth1` do `r-filial`, o `snmpwalk` acima dá **`Timeout: No Response`** porque não passa pela `eth0`.

---

## 3. A Pilha Zabbix (`172.20.99.10–12`)

### Como os 3 contêineres em `integrante_A/zabbix/docker-compose.yml` trabalham juntos
1. **`postgres-server` (`.12`):** o banco de dados que guarda toda a configuração do Zabbix e o histórico das medições.
2. **`zabbix-server` (`.10`):** o motor que dispara consultas SNMP/Agent/ICMP (porta `10051`) e avalia quando um problema aconteceu. *(Na primeira vez que sobe, ele leva ~30–90s criando as tabelas no PostgreSQL — antes disso a tela web mostra `table "dbversion" was not found`.)*
3. **`zabbix-web` (`.11`):** a tela web que abrimos em `http://127.0.0.1:8080` (`Admin` / `zabbix`).

### O que é "Dependência de Trigger" no Zabbix (muito cobrado!)
Imagine que o roteador `r-filial` caiu. Automaticamente, `cliente-carga` e `sonda` atrás dele também ficam sem resposta.
- **Sem dependência:** o Zabbix dispara 3 alertas críticos ao mesmo tempo (tempestade de alertas).
- **Com dependência:** dizemos ao Zabbix que `cliente-carga` e `sonda` **dependem** do `r-filial`. Se `r-filial` cair, o Zabbix mostra **apenas 1 problema raiz (`r-filial` fora)** e silencia os sintomas em cascata.

*(Lembrando: concluir os agentes nos hosts da matriz, cenário web, dependências de triggers, mapa e alerta do Zabbix é tarefa da Integrante A.)*
