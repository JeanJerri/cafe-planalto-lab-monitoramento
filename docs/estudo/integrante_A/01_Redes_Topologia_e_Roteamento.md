# A1 — Redes, Topologia e Roteamento Estático (Do Zero)

Mesmo que a topologia de rede seja tarefa da Integrante A, você precisa entender **a lógica do caminho** por onde os pedidos da sua loja trafegam. Vamos aprender acompanhando a viagem de **um único pacote** saindo da Filial até a Matriz.

---

## 1. Interfaces (`eth0`, `eth1`, `eth2`), MAC e IP

### Por que isso existe?
Para dois computadores conversarem, cada um precisa de uma "tomada" para ligar o cabo (interface) e de dois endereços diferentes:
- **Endereço MAC** (ex.: `a8:c1:ab:f7:dd:77`): é o "CPF gravado na placa de rede". Ele só serve para entregar um pacote **dentro da mesma sala/rede local**.
- **Endereço IP** (ex.: `172.20.10.21`): é o "CEP + número da casa". Ele permite atravessar várias cidades (redes) até o destino final.

### Como funciona no Linux?
Cada entrada de cabo virtual no Linux ganha um nome (`eth0`, `eth1`, `eth2`...):
- Um computador comum da loja (`api` ou `cliente-carga`) tem **2 entradas**: `eth0` (administração, proibida para a loja) e `eth1` (rede da empresa).
- Um **roteador** (`r-matriz`) tem **4 entradas** (`eth0` administração, `eth1` WAN, `eth2` LAN Serviços, `eth3` LAN Gerência), porque o trabalho dele é justamente ligar várias redes diferentes.

### Onde está e como validar (10 segundos)
Em [`integrante_A/infra/topology.yml`](../../integrante_A/infra/topology.yml), cada bloco `links:` liga duas pontas (ex.: `["r-matriz:eth1", "r-filial:eth1"]`).
Ao rodar `sudo docker exec clab-cafeplanalto-r-matriz ip -br addr`, você vê cada placa e o IP colado nela.

---

## 2. Máscara CIDR (`/24`, `/30`, `/16`) e Gateway

### Por que isso existe? (Sem matemática complicada!)
Quando você lê `172.20.10.21/24`, como o computador sabe qual parte do número é o **"nome da rua (rede)"** e qual parte é o **"número da casa (computador)"**? Quem diz isso é o `/24` no final!

Um IPv4 tem **4 blocos que somam 32 bits** (8 bits por bloco):
- **`/24`** = os **3 primeiros números** identificam a rua (`172.20.10.x`), e o último número identifica até 254 aparelhos (`.1` a `.254`). É o padrão das nossas 3 LANs.
- **`/16`** = os **2 primeiros números** identificam o bairro inteiro (`172.20.x.x`), englobando todas as LANs da empresa de uma vez só.
- **`/30`** = sobram apenas **2 bits livres (`4` endereços no total)**! Como o primeiro (`.0`) é o nome da rua e o último (`.3`) é o grito geral (*broadcast*), **sobram exatamente 2 IPs usáveis**:
  - `10.0.0.1` → ponta do `r-matriz`
  - `10.0.0.2` → ponta do `r-filial`

> **Pergunta certa da prova:** *"Por que a WAN usa `/30` e não `/24`?"*
> Porque um cabo ponto a ponto entre dois roteadores só tem **2 pontas**. Usar `/30` dá exatamente os 2 IPs necessários sem desperdiçar 252 endereços.

### O que é o Gateway?
Se o `cliente-carga` (`172.20.20.20`) quer falar com alguém da mesma rua (`172.20.20.30`), ele entrega direto. Mas se quer falar com outra rua (`172.20.10.21`), ele entrega na portaria da própria rua: o **Gateway**, que por padrão fica no IP **`.1`** (`172.20.20.1` na Filial; `172.20.10.1` na Matriz).

---

## 3. Switch/Bridge (Camada 2) vs. Roteador (Camada 3) e `ip_forward=1`

### Por que isso existe?
- **Switch / Bridge Linux (`sw-servicos`, `sw-filial`, `sw-gerencia`):** é como uma **régua de tomadas inteligente** (Camada 2). Só liga aparelhos da **mesma LAN** olhando endereços MAC. Ele não entende IP de outra rede.
- **Roteador (`r-matriz`, `r-filial`):** é o **cruzamento entre redes** (Camada 3). Ele olha o IP de destino e decide por qual cabo (`eth1`, `eth2` ou `eth3`) o pacote deve seguir.

### Por que precisamos de `sysctl -w net.ipv4.ip_forward=1`?
Por segurança, um Linux comum nasce **proibido de repassar pacotes** (`ip_forward = 0`): se chegar um pacote na `eth2` com destino à `eth1`, ele joga no lixo. Ligar `ip_forward=1` no kernel transforma o contêiner Alpine em um roteador de verdade.

### Valide + "E se eu tirasse isso?"
```bash
sudo docker exec clab-cafeplanalto-r-matriz sysctl net.ipv4.ip_forward
# Tem que mostrar: net.ipv4.ip_forward = 1
```
**Se fosse `0`:** o `ping` da Filial chegaria no `r-filial` e morreria lá mesmo — nenhum pedido atravessaria a WAN.

---

## 4. Tabela de Rotas Estáticas e *Longest Prefix Match*

### Como o Linux decide entre `eth0` (proibida) e `eth1` (correta)?
Olhe o `ip route` real de qualquer servidor nosso:
- `default via 172.30.0.1 dev eth0` → vale para **qualquer IP do mundo** (`/0` = 0 bits fixos = super genérica).
- `172.20.0.0/16 via 172.20.20.1 dev eth1` → vale especificamente para a rede da empresa (`/16` = 16 bits fixos).

**Regra do Linux (*Longest Prefix Match*):** quando duas placas servem para o mesmo destino, **sempre vence a rota mais específica (maior número depois da `/`)**! Como `/16` vence `/0`, o pacote é obrigado a sair pela `eth1`!

### A viagem completa de `cliente-carga` (`172.20.20.20`) até `api` (`172.20.10.21`)
```text
[cliente-carga] ──(eth1)──► [sw-filial] ──► [r-filial] ──(WAN 10.0.0.0/30)──► [r-matriz] ──► [sw-servicos] ──► [api]
  172.20.20.20                             172.20.20.1   10.0.0.2 -> 10.0.0.1    10.0.0.1                       172.20.10.21
```

### Valide em 10 segundos (`ping` e `traceroute`)
1. `ping -c 2 172.20.10.21`: no Linux, todo pacote nasce com **`TTL = 64`** (um contador que evita pacotes rodando em círculo para sempre). Cada roteador subtrai `1`. Como atravessamos `r-filial` e `r-matriz` (2 roteadores), o ping chega com **`ttl=62`**.
2. `traceroute -n 172.20.10.21`: ele envia pacotes testando 1 salto, 2 saltos, 3 saltos. Cada roteador responde com o IP da **porta de entrada** por onde o pacote chegou nele:
   - Salto 1: `172.20.20.1` (`eth2` do `r-filial`)
   - Salto 2: `10.0.0.1` (`eth1` do `r-matriz`)
   - Salto 3: `172.20.10.21` (`api`)

---

## 5. Falha 1 (`eth1 down`) vs. Falha 2 (`ip route del`) — Qual a diferença?

| Falha simulada | O que muda na prática | Como o Zabbix/Prometheus enxerga |
| --- | --- | --- |
| **Falha 1:** `ip link set eth1 down` | "Desplugou o cabo" da placa `eth1`. *(Atenção: o Linux apaga automaticamente as rotas estáticas que saíam por ela; ao religar `up`, é preciso readicionar as rotas!)* | SNMP mostra interface **`DOWN`**, ping falha e sonda some (`up == 0`). |
| **Falha 2:** `ip route del 172.20.20.0/24` | O cabo continua ligado, mas "arrancaram a placa de trânsito" na tabela do roteador. | SNMP continua **`UP`**, mas o ping e a loja falham porque o roteador não sabe o caminho de volta. |

---

## 6. Simulado Rápido (Responda sem olhar)
1. Por que a WAN usa `/30`? *(2 pontas utilizáveis + rede + broadcast = 4 IPs, zero desperdício.)*
2. Para que serve `net.ipv4.ip_forward=1`? *(Permite ao kernel Linux repassar pacotes entre placas; sem ele o roteador descarta tráfego de terceiros.)*
3. Como sabemos que o tráfego atravessou os 2 roteadores e não vazou pela `eth0`? *(Pelo `traceroute` mostrando `172.20.20.1 → 10.0.0.1`, pelo `ttl=62` no `ping`, e porque ao derrubar `eth1` o `ping` perde 100%.)*
