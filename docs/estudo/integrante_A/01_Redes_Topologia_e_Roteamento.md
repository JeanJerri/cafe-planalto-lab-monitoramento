# A1 — Redes, Topologia Containerlab e Roteamento Estático (Integrante A)

Este módulo explica do zero como funciona a rede construída pela Integrante A em [`integrante_A/infra/`](../../integrante_A/infra/). Dominar este conteúdo garante segurança na **arguição individual cruzada** e ajuda você a entender por onde trafegam os pacotes da sua aplicação.

---

## 1. Fundamentos do Zero

### 1.1 O que é uma Interface de Rede (`eth0`, `eth1`, `eth2`, `eth3`)?
Pense nas entradas de cabo de rede atrás de um computador ou roteador. No Linux, cada placa virtual recebe um nome (`eth0`, `eth1`...):
- Um **servidor ou cliente** (`api`, `dns`, `cliente-carga`) tem normalmente 2 placas:
  - `eth0`: rede de gerência fora de banda (`172.30.0.0/24`), usada só pelo Docker/Containerlab para administração e internet.
  - `eth1`: placa ligada na LAN da empresa (`172.20.x.x`), por onde trafega a loja e o monitoramento real.
- Um **roteador** (`r-matriz`, `r-filial`) tem várias placas porque sua função é justamente interligar redes diferentes:
  - `r-matriz`: `eth1` (WAN `10.0.0.1/30`), `eth2` (LAN Serviços `172.20.10.1/24`), `eth3` (LAN Gerência `172.20.99.1/24`).
  - `r-filial`: `eth1` (WAN `10.0.0.2/30`), `eth2` (LAN Filial `172.20.20.1/24`).

### 1.2 Endereço MAC vs. Endereço IP
- **MAC:** identificador de hardware gravado na placa de rede. Só funciona para entregar quadros **dentro da mesma rede local (LAN)**.
- **IP:** endereço lógico hierárquico (como CEP + número). Permite que um pacote saia da Filial, atravesse roteadores e chegue à Matriz.

### 1.3 Máscara CIDR (`/30`, `/24`, `/16`) e Gateway
Um IPv4 tem **32 bits** divididos em 4 números de 0 a 255. A notação `/N` indica quantos bits identificam a **rede** ("a rua") e quantos sobram para os **hosts** ("as casas"):

| Notação CIDR | Bits de Rede | Bits de Host | IPs utilizáveis | Uso no laboratório |
| --- | --- | --- | --- | --- |
| **`/24`** (`255.255.255.0`) | 24 | 8 (`256` total) | `254` (`.1` a `.254`) | `172.20.10.0/24`, `172.20.20.0/24`, `172.20.99.0/24` |
| **`/30`** (`255.255.255.252`) | 30 | 2 (`4` total) | **Apenas `2`** (`.1` e `.2`) | Enlace WAN ponto a ponto `10.0.0.0/30` |
| **`/16`** (`255.255.0.0`) | 16 | 16 (`65.536` total) | Todas as sub-redes `172.20.x.x` | Rota resumida nos servidores |

> **Por que a WAN usa `/30`?** Porque um enlace ponto a ponto tem exatamente 2 pontas (`r-matriz` em `10.0.0.1` e `r-filial` em `10.0.0.2`), mais o endereço de rede (`10.0.0.0`) e o broadcast (`10.0.0.3`). Usar `/30` evita desperdício de IPs.

**O que é o Gateway?**
Quando `cliente-carga` (`172.20.20.20`) quer falar com `172.20.10.20` (outra rede), ele entrega o pacote ao **gateway** da sua LAN — sempre o `.1` (`172.20.20.1`, que é o `r-filial`).

---

## 2. Switch/Bridge (Camada 2) vs. Roteador (Camada 3)

- **Switch / Bridge Linux (`sw-servicos`, `sw-filial`, `sw-gerencia`):** opera na **Camada 2 (Enlace)**. Interliga dispositivos da **mesma LAN** olhando endereços MAC. Não sabe cruzar de uma rede IP para outra.
- **Roteador (`r-matriz`, `r-filial`):** opera na **Camada 3 (Rede)**. Liga redes diferentes e decide o próximo salto (*next hop*) olhando a tabela de rotas e o IP de destino.

### O comando `sysctl -w net.ipv4.ip_forward=1`
Por padrão, qualquer Linux comum descarta pacotes que chegam em uma interface destinados a outro IP (`ip_forward = 0`), por segurança. Rodar `sysctl -w net.ipv4.ip_forward=1` no kernel transforma o contêiner Alpine em um roteador capaz de encaminhar pacotes entre `eth1`, `eth2` e `eth3`.

---

## 3. Tabela de Rotas Estáticas e *Longest Prefix Match*

**Roteamento estático** significa configurar cada caminho manualmente no `topology.yml`, sem protocolos dinâmicos (OSPF/BGP):

```text
ip route add 172.20.20.0/24 via 10.0.0.2
```
Leia assim: *"Para alcançar qualquer IP da rede `172.20.20.0/24`, envie o pacote ao próximo roteador `10.0.0.2`."*

### Como o Linux garante que o pacote NÃO escape pela `eth0`?
Pela regra do **Longest Prefix Match (Vence a Rota Mais Específica)**:
- A rota `default via 172.30.0.1 dev eth0` tem prefixo `/0` (0 bits fixos — último recurso).
- As rotas dos servidores (`172.20.0.0/16` e `10.0.0.0/30` via gateway `.1`) têm prefixos `/16` e `/30`.
- Como `/30 > /24 > /16 > /0`, qualquer tráfego para dentro do laboratório vence a `default` e obrigatoriamente atravessa a `eth1` e os roteadores!

**Viagem completa de um pacote (Filial → Matriz):**
1. `cliente-carga` (`172.20.20.20`) envia para `172.20.10.20` via `eth1` → `sw-filial` → `r-filial` (`172.20.20.1`).
2. `r-filial` consulta `172.20.10.0/24 via 10.0.0.1` e encaminha pela WAN (`eth1`) até `10.0.0.1` (`r-matriz`).
3. `r-matriz` vê que `172.20.10.0/24` está diretamente conectada na sua `eth2` e entrega via `sw-servicos` ao destino.

---

## 4. `ping`, `TTL` e `traceroute`

- **`ping`:** envia pacotes ICMP Echo Request e mede disponibilidade, perda (%) e tempo de ida e volta (RTT em `ms`).
- **`TTL` (*Time To Live*):** contador que começa em `64` no Linux e diminui `-1` a cada roteador atravessado (impede loops infinitos). Como o pacote passa por `r-filial` e `r-matriz` (2 roteadores), chega ao destino com **`ttl=62`**.
- **`traceroute`:** descobre cada salto no caminho enviando pacotes com `TTL=1`, `TTL=2`, `TTL=3`. Cada roteador responde com o IP da **interface por onde o pacote entrou nele**:
  1. `172.20.20.1` (`eth2` do `r-filial`)
  2. `10.0.0.1` (`eth1` do `r-matriz`)
  3. `172.20.10.21` (destino na LAN Serviços)

---

## 5. O que existe em `integrante_A/infra/topology.yml`

No arquivo atual [`integrante_A/infra/topology.yml`](../../integrante_A/infra/topology.yml), a Integrante A já estruturou:
- As 3 bridges Linux (`sw-servicos`, `sw-filial`, `sw-gerencia`).
- Os 2 roteadores (`r-matriz`, `r-filial`) com `ip_forward=1`, IPs da WAN e das 3 LANs, rotas estáticas e daemon `snmpd` rodando em segundo plano.
- Nós de apoio para os testes iniciais (`api` provisório, `cliente-carga` provisório, `host-gerencia` em `172.20.99.100` e `dns` CoreDNS).
- **Correção pontual já aplicada na Fase 1:** o nó `dns` estava com IP `172.20.10.53` e domínio `cafeplanalto.test`, e faltava a rota `10.0.0.0/30` em `dns` e `host-gerencia`. Ajustamos para `172.20.10.10` (`cafeplanalto.lab`) e adicionamos as rotas para a WAN.

---

## 6. Simulado de Arguição (Perguntas da Parte A)

1. **Por que a WAN usa `/30` (`10.0.0.0/30`) e não `/24`?**
   > Porque um link ponto a ponto precisa de apenas 2 IPs utilizáveis (`.1` e `.2`), além do endereço de rede (`.0`) e broadcast (`.3`), evitando desperdício de endereços.
2. **O que acontece se esquecer `net.ipv4.ip_forward=1` no `r-matriz`?**
   > O kernel trata o contêiner como um host comum e descarta pacotes recebidos da Filial que tenham como destino a LAN Serviços ou Gerência; o `ping` da Filial para a loja falha.
3. **Qual a diferença entre derrubar `eth1` (Falha 1) e remover a rota estática (Falha 2)?**
   > Na Falha 1 (`ip link set eth1 down`), a interface física/virtual cai e aparece como `DOWN` no SNMP. Na Falha 2 (`ip route del`), as interfaces continuam `UP` no SNMP, mas o roteador não sabe para onde encaminhar o pacote e o descarta por falta de rota.
4. **Por que o tráfego não pode passar pela `eth0`?**
   > Porque `eth0` (`172.30.0.0/24`) interliga todos os contêineres paralelamente fora do laboratório. Se o monitoramento ou a loja usassem `eth0`, uma queda da WAN não interromperia o tráfego e a falha ficaria invisível.
