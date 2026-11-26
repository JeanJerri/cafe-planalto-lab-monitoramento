# Guia Completo de Estudo, Análise e Integração — Infraestrutura (Integrante A)

Este guia foi escrito como uma **escada passo a passo para quem está começando do zero**. Primeiro construímos a teoria de redes sem pular etapas, depois explicamos cada arquivo que a Integrante A entregou, e por fim mostramos **exatamente onde estão as pastas no seu computador, qual terminal abrir e quais comandos digitar para testar e unir tudo com a sua API**.

> **Por que você precisa dominar a parte da Integrante A?**
> No roteiro oficial da disciplina, durante a apresentação cada aluno responde uma pergunta na **arguição individual sobre a parte que NÃO apresentou**. Além disso, a loja (sua API) precisa rodar dentro da rede que ela criou.

---

## Etapa 1 — Fundamentos de Rede do Zero (Placa de Rede, MAC, IP, LAN e WAN)

### 1.1 O que é uma Interface de Rede (`eth0`, `eth1`, `eth2`)?
Pense nas **entradas de cabo de rede** atrás de um computador ou roteador. No Linux, essas interfaces virtuais recebem nomes como `eth0`, `eth1`, `eth2`:
- Um servidor normal da loja (`api` ou `cliente-carga`) tem **2 entradas**:
  - `eth0`: rede de gerência administrativa (explicada na Etapa 3).
  - `eth1`: cabo que liga o servidor à rede da empresa (dados reais).
- Um roteador (`r-matriz`) tem **várias entradas** (`eth0`, `eth1`, `eth2`...) porque ele serve justamente para conectar redes diferentes entre si.

### 1.2 Endereço MAC vs. Endereço IP
- **Endereço MAC** (ex.: `aa:c1:ab:40:b0:d5`): é o "CPF físico" gravado na placa de rede. Só funciona para entregar pacotes **dentro da mesma sala/rede local**.
- **Endereço IP** (ex.: `172.20.10.21`): é o "CEP + número da casa". Serve para localizar qualquer computador **mesmo quando ele está em outra cidade/rede**, atravessando vários roteadores.

### 1.3 LAN vs. WAN
- **LAN (*Local Area Network*):** rede interna de um único prédio. No projeto temos a **LAN Filial** e a **LAN Serviços (Matriz)** (e nas Semanas 2–3 entrará a **LAN Gerência**).
- **WAN (*Wide Area Network*):** o link de longa distância que liga o prédio da Matriz ao prédio da Filial.

---

## Etapa 2 — IP, Máscara CIDR (`/16`, `/24`, `/30`) e Gateway Explicados do Zero

### 2.1 Como ler um IP e uma máscara (`/24`, `/30`, `/16`)
Todo IPv4 é formado por **4 números de 0 a 255** (total de **32 bits**, sendo 8 bits por número):
`172 . 20 . 10 . 21`

A barra no final (notação **CIDR**) diz **quantos desses 32 bits são fixos para identificar a "rua" (a rede)** e quantos bits sobram livres para numerar as "casas" (os aparelhos):

| Notação CIDR | Bits fixos (Rede) | Bits livres (Hosts) | Total de IPs na faixa | Uso no trabalho |
| --- | --- | --- | --- | --- |
| **`/24`** (`255.255.255.0`) | 24 bits (os 3 primeiros números) | 8 bits (`2⁸ = 256` IPs) | 254 usáveis (`.1` a `.254`) | As LANs: `172.20.10.0/24` (Serviços) e `172.20.20.0/24` (Filial) |
| **`/30`** (`255.255.255.252`) | 30 bits | 2 bits (`2² = 4` IPs) | **Apenas 2 usáveis** (`.1` e `.2`) | A **WAN** `10.0.0.0/30` |
| **`/16`** (`255.255.0.0`) | 16 bits (os 2 primeiros números) | 16 bits (`65.536` IPs) | Todas as sub-redes `172.20.x.x` | Rota resumida nos servidores (`172.20.0.0/16`) |

**Regra importante de qualquer rede:** o primeiro IP da faixa é o **endereço da rede** (identifica a rua) e o último IP é o **broadcast** (gritar para todos). Nenhum computador pode usar esses dois extremos.

**Por que a WAN usa `/30` (`10.0.0.0/30`)?**
Como o cabo da WAN só tem **duas pontas** (`r-matriz` e `r-filial`), usar `/30` cria exatamente os 4 endereços necessários sem desperdiçar IPs:
- `10.0.0.0` → endereço da rede WAN (reservado)
- **`10.0.0.1`** → ponta do **`r-matriz`**
- **`10.0.0.2`** → ponta do **`r-filial`**
- `10.0.0.3` → broadcast (reservado)

### 2.2 O que é o Gateway?
Quando o `cliente-carga` (`172.20.20.20`) quer conversar com alguém da **mesma rede** (`172.20.20.x`), ele entrega direto pelo switch.
Quando ele quer conversar com outra rede (`172.20.10.21`), ele não sabe o caminho sozinho: ele entrega o pacote na porta do **Gateway** (o roteador da sua própria rede, que por padrão fica no `.1`, ou seja, `172.20.20.1` na Filial e `172.20.10.1` na Matriz).

---

## Etapa 3 — Switch/Bridge vs. Roteador, Kernel Linux e Tabela de Rotas

### 3.1 Switch / Bridge Linux (Camada 2) vs. Roteador (Camada 3)
- **Switch / Bridge Linux (`sw-servicos`, `sw-filial`):** funciona como uma "régua de tomadas" inteligente dentro da **mesma LAN**. Liga dispositivos da mesma faixa IP usando endereços MAC (Camada 2). Não sabe atravessar para outra rede.
- **Roteador (`r-matriz`, `r-filial`):** é um computador com mais de uma placa de rede conectado a **redes diferentes** que decide para onde enviar cada pacote olhando o endereço IP de destino (Camada 3).

### 3.2 O que é o Kernel Linux e `sysctl -w net.ipv4.ip_forward=1`?
- **Kernel:** é o núcleo do sistema operacional Linux, responsável por controlar placa de rede, memória e pacotes.
- Por segurança, um servidor Linux comum nasce com o encaminhamento desligado (`ip_forward = 0`): se chegar um pacote endereçado a outro IP que não seja o dele, ele joga fora.
- O comando **`sysctl -w net.ipv4.ip_forward=1`** liga a chave do encaminhamento no kernel, transformando o contêiner Alpine comum em um roteador capaz de passar pacotes da interface `eth2` (LAN) para a `eth1` (WAN) e vice-versa.

### 3.3 Lendo uma Tabela de Rotas Estáticas
**Roteamento estático** significa que nós mesmos escrevemos as placas de trânsito na mão (`ip route add`), sem protocolos automáticos. Veja como ler uma linha de rota:

```text
ip route add 172.20.20.0/24 via 10.0.0.2
```
Leia em português assim: *"Para qualquer pacote tentando chegar na rede **`172.20.20.0/24`**, entregue-o para o próximo roteador (**`via 10.0.0.2`**)."*

### 3.4 Rede de Gerência (`eth0`) vs. Rede de Dados (`eth1`/`eth2`) e *Longest Prefix Match*
Quando o Containerlab sobe qualquer contêiner, ele cria automaticamente a placa **`eth0`** na rede **`172.30.0.0/24`** (`clab-mgmt`) e coloca uma rota padrão (`default via 172.30.0.1 dev eth0`). Essa `eth0` existe **só para administração e internet**.

**A Regra de Ouro do trabalho:** o tráfego da loja (`cliente-carga -> api`) e de monitoramento **nunca pode usar a `eth0`**! Se usasse, quando o professor derrubasse a WAN (`eth1`), os pacotes escapariam pela `eth0` e o problema ficaria escondido.

**Como o Linux escolhe a `eth1` e não a `eth0`?**
Pela regra do **Longest Prefix Match (Vence a Rota Mais Específica)**:
- A rota `default` pela `eth0` equivale a `/0` (0 bits fixos = serve para qualquer coisa, último recurso).
- A rota dos servidores `172.20.0.0/16 via 172.20.20.1` fixa **16 bits** (`/16 > /0`).
- A rota dos roteadores `172.20.10.0/24 via 10.0.0.1` fixa **24 bits** (`/24 > /0`).

**Acompanhe a viagem completa de um pacote do `cliente-carga` até a `api`:**
1. `cliente-carga` (`172.20.20.20`) quer falar com `172.20.10.21`. Ele olha sua tabela: a rota `172.20.0.0/16` (`/16`) vence a `default` (`/0`), então ele manda pela `eth1` até `sw-filial` rumo ao gateway **`172.20.20.1`** (`r-filial`).
2. `r-filial` recebe pela `eth2`, vê `ip_forward=1`, olha a rota `172.20.10.0/24 via 10.0.0.1` (`/24` vence `/0`) e envia o pacote pela WAN (`eth1`) até **`10.0.0.1`** (`r-matriz`).
3. `r-matriz` recebe pela `eth1` e vê que `172.20.10.0/24` está diretamente ligada na sua própria interface `eth2`. Ele entrega o pacote pelo `sw-servicos` até a **`api` (`172.20.10.21`)**.
4. Na volta, a `api` usa sua rota `172.20.0.0/16 via 172.20.10.1` e faz exatamente o caminho inverso pela WAN!

---

## Etapa 4 — Entendendo as Ferramentas: WSL2, Ubuntu, Containerlab, `ping` e `traceroute`

- **Por que precisamos do Ubuntu / WSL2 no Windows?**
  O **Containerlab** cria placas de rede virtuais (`veth`), bridges de rede no kernel e isola tabelas de rotas por contêiner (namespaces de rede). Isso só existe no **kernel Linux**. No Windows, usamos o **WSL2** (*Windows Subsystem for Linux*), que roda um **Ubuntu Linux real** integrado dentro do Windows.
- **Comandos básicos que você vai usar:**
  - `sudo`: executa o comando como administrador (root) no Linux (Containerlab e configuração de rede exigem `sudo`).
  - `docker exec <nome_container> <comando>`: entra "por dentro" de um contêiner que já está rodando para executar um comando nele (ex.: rodar `ping` de dentro do `cliente-carga`).
  - **Alpine Linux (`alpine:3`):** uma distribuição Linux super enxuta (poucos MB) que usa o gerenciador de pacotes **`apk`** (por isso `apk add ...` no Dockerfile da Integrante A).
  - **YAML (`.yml`):** formato de arquivo de configuração organizado por **indentação com espaços** (`topology.yml`). Nunca use Tab no YAML, apenas espaços alinhados!
- **`ping`, `TTL` e `traceroute`:**
  - **`ping`:** envia pacotes de teste ICMP e mede se chegam, quanto tempo levam (ms) e se há perda.
  - **`TTL` (*Time To Live*):** todo pacote no Linux nasce com `TTL = 64`. Cada roteador que ele atravessa subtrai `1` (evita pacotes girando em loop infinito). Como no ambiente da dupla o pacote atravessa `r-filial` e `r-matriz` (2 roteadores), ele chega com **`ttl=62`** (`64 - 2 = 62`).
  - **`traceroute`:** descobre todos os roteadores no caminho enviando pacotes com `TTL=1`, depois `TTL=2`, etc. Por padrão IP, cada roteador responde com o IP da **interface por onde o pacote entrou nele**:
    - Salto 1: `172.20.20.1` (interface `eth2` de entrada do `r-filial`).
    - Salto 2: `10.0.0.1` (interface `eth1` de entrada do `r-matriz`).
    - Salto 3: `172.20.10.21` (destino final: `api`).

---

## Etapa 5 — Onde Estão as Pastas Hoje e Análise do que a Integrante A Fez

Neste momento, no seu computador Windows existem **duas pastas separadas**:

```text
C:\Users\jeanj\Projetos\Projeto_E_Administracao_De_Redes\Projeto_Final\
│
├── app\                                 <-- SUA PASTA (Integrante B: código da API FastAPI)
│   ├── src\, tests\, docs\
│   ├── Dockerfile, requirements.txt, .env.example, .dockerignore, README.md
│   └── .venv\, .agente\, .git\
│
└── integrante_A\                        <-- PASTA QUE ELA ENVIOU (extraída do Ubuntu/WSL dela)
    ├── (.bashrc, .cache, .config, .local, .tar, .tar.gz)  <-- sobras da pasta home dela (IGNORAR)
    └── cafeplanalto\                    <-- AQUI ESTÁ O PROJETO REAL DA INTEGRANTE A!
        ├── README.md                    <-- Resumo e comandos do Checkpoint 1
        ├── app\.gitkeep                 <-- Pasta vazia reservada para receber a sua API!
        ├── evidencias\checkpoint1.txt   <-- Provas reais de rotas, ip_forward, ping e traceroute
        ├── infra\
        │   ├── Dockerfile               <-- Receita da imagem cafeplanalto/netlab:1.0 (Alpine 3)
        │   ├── topology.yml             <-- Topologia Containerlab (6 nós, IPs, rotas estáticas)
        │   └── clab-cafeplanalto\       <-- Gerada automaticamente no PC dela (livia) -> NÃO USAR/NÃO SUBIR NO GIT
        ├── prometheus\.gitkeep          <-- Reservada para a Semana 3
        └── zabbix\.gitkeep              <-- Reservada para a Semana 2
```

### 5.1 O desenho da topologia que a Integrante A montou

```text
  [cliente-carga]                      [r-filial]          WAN          [r-matriz]                     [api]
  172.20.20.20/24  ──[sw-filial]──  eth2: 172.20.20.1     10.0.0.0/30   eth1: 10.0.0.1  ──[sw-servicos]── eth1: 172.20.10.21/24
     (eth1)                           eth1: 10.0.0.2  ───────────────── eth2: 172.20.10.1                   (LAN Serviços)
   (LAN Filial)

  Todas as máquinas também têm eth0 (172.30.0.0/24 - clab-mgmt) apenas para gerência fora de banda.
```

| Nó no `topology.yml` | Tipo | Imagem atual | IPs configurados | Rotas estáticas configuradas (`exec`) |
| --- | --- | --- | --- | --- |
| `r-matriz` | `linux` | `cafeplanalto/netlab:1.0` | `eth1`: `10.0.0.1/30`, `eth2`: `172.20.10.1/24` | `172.20.20.0/24 via 10.0.0.2` (+ `ip_forward=1`) |
| `r-filial` | `linux` | `cafeplanalto/netlab:1.0` | `eth1`: `10.0.0.2/30`, `eth2`: `172.20.20.1/24` | `172.20.10.0/24 via 10.0.0.1` (+ `ip_forward=1`) |
| `sw-servicos` | `bridge` | *(bridge do Linux)* | Portas `sv-rmat` e `sv-api` | — |
| `sw-filial` | `bridge` | *(bridge do Linux)* | Portas `sf-rfil` e `sf-cli` | — |
| `api` | `linux` | `cafeplanalto/netlab:1.0` *(provisório)* | `eth1`: `172.20.10.21/24` | `172.20.0.0/16` e `10.0.0.0/30 via 172.20.10.1` |
| `cliente-carga` | `linux` | `cafeplanalto/netlab:1.0` | `eth1`: `172.20.20.20/24` | `172.20.0.0/16` e `10.0.0.0/30 via 172.20.20.1` |

### 5.2 Análise técnica e Pontos de Atenção encontrados
1. **Checkpoint 1 validado e sólido:** no `evidencias/checkpoint1.txt`, o `r-matriz` e o `r-filial` aparecem com `net.ipv4.ip_forward = 1`, todas as rotas batem, o `ping` de `cliente-carga` para `172.20.10.21` deu `0% packet loss` e `ttl=62`, e o `traceroute` passou por `172.20.20.1 -> 10.0.0.1 -> 172.20.10.21`.
2. **`curl` não está instalado em `infra/Dockerfile`:** a imagem `cafeplanalto/netlab:1.0` instala `iproute2`, `iputils`, `traceroute` e `procps`, mas faltou `curl`. Quando você entrar no `cliente-carga` para testar sua API, terá que usar `wget -qO-` ou adicionar `curl` ao `infra/Dockerfile` (mostrado na Etapa 7).
3. **`infra/clab-cafeplanalto/` antigo deve ser apagado antes do deploy:** essa subpasta foi gerada automaticamente quando o Containerlab rodou no usuário `livia` (como consta em `topology-data.json`) e contém chaves privadas em `.tls/ca/ca.key`. Ela deve ser removida antes de rodar na sua máquina e nunca ir para o Git.
4. **Itens que ficam para as Semanas 2–3 (normal):** `LAN Gerência` (`172.20.99.0/24` e `eth3` no `r-matriz`), `net-snmp` nos roteadores, `dns` (CoreDNS), `web` (Nginx), `db` (PostgreSQL) e `Makefile` (`make up`).

---

## Etapa 6 — Passo a Passo Prático: Como Chegar na Pasta no Ubuntu (WSL2) e Testar a Infraestrutura

### 6.1 Entendendo o caminho entre Windows e Ubuntu (WSL2)
No Ubuntu dentro do **WSL2**, o seu disco `C:\` do Windows aparece montado dentro da pasta **`/mnt/c/`** (tudo com barra normal `/` em vez de `\`). Ou seja:
- Sua pasta `app` no Ubuntu fica em:
  `/mnt/c/Users/jeanj/Projetos/Projeto_E_Administracao_De_Redes/Projeto_Final/app`
- A pasta `cafeplanalto` da Integrante A no Ubuntu fica em:
  `/mnt/c/Users/jeanj/Projetos/Projeto_E_Administracao_De_Redes/Projeto_Final/integrante_A/cafeplanalto`

**Regra prática recomendada:** em vez de rodar o Containerlab diretamente dentro de `/mnt/c/...` (que é mais lento para Docker/permissões Linux e mexeria nos arquivos originais dela), vamos **copiar** a pasta `cafeplanalto` para a sua pasta pessoal do Linux (**`~/cafeplanalto`**, onde `~` significa `/home/seu_usuario`)!

### 6.2 Abrir o terminal Ubuntu e conferir se o ambiente está instalado
1. Pressione a tecla **Windows**, digite **`Ubuntu`** e abra o terminal do Ubuntu (ou digite `wsl` no PowerShell).
2. Confira se Docker e Containerlab estão instalados no seu Ubuntu:

```bash
docker --version
sudo docker info --format "{{.ServerVersion}}"
containerlab version
```

- **Se todos responderem com a versão:** ótimo, siga para o passo 6.3!
- **Se `containerlab` (ou `docker`) der "command not found":** significa que o laboratório foi rodado até agora no WSL2/VM do computador da Integrante A e ainda não foi instalado no seu Windows/WSL2. Você tem duas opções:
  1. Seguir os comandos abaixo **no computador/VM dela** quando forem juntar e apresentar; **ou**
  2. Instalar Docker + Containerlab no seu Ubuntu WSL2 seguindo as instruções oficiais do Containerlab (`curl -sL https://containerlab.dev/setup | sudo -E bash -s "all"` após habilitar Docker no WSL2).

### 6.3 Copiar `cafeplanalto` para `~/cafeplanalto` e limpar o cache antigo
No terminal **Ubuntu (WSL2)**, rode exatamente estes comandos:

```bash
# 1. Copia a pasta cafeplanalto (da Integrante A) para sua home no Linux (~/cafeplanalto)
cp -r "/mnt/c/Users/jeanj/Projetos/Projeto_E_Administracao_De_Redes/Projeto_Final/integrante_A/cafeplanalto" ~/cafeplanalto

# 2. Remove a pasta antiga gerada na máquina da Integrante A (será recriada limpa)
rm -rf ~/cafeplanalto/infra/clab-cafeplanalto

# 3. Entra dentro da pasta cafeplanalto
cd ~/cafeplanalto

# 4. Confirma que você está no lugar certo e lista o conteúdo
pwd
ls -la
```

**O que deve aparecer:**
- `pwd` mostra `/home/<seu_usuario>/cafeplanalto`.
- `ls -la` mostra `README.md`, `app`, `evidencias`, `infra`, `prometheus`, `zabbix`.

### 6.4 Testar SÓ a Infraestrutura da Integrante A (Checkpoint 1)
Ainda dentro de `~/cafeplanalto` no terminal Ubuntu:

```bash
# Passo 1: Construir a imagem Docker usada pelos roteadores e nós de rede
sudo docker build -t cafeplanalto/netlab:1.0 ./infra

# Passo 2: Criar e ligar os dois switches virtuais (bridges Linux)
sudo ip link add name sw-servicos type bridge 2>/dev/null || true
sudo ip link set sw-servicos up
sudo ip link add name sw-filial type bridge 2>/dev/null || true
sudo ip link set sw-filial up

# Passo 3: Subir a topologia no Containerlab (lê infra/topology.yml)
sudo containerlab deploy -t infra/topology.yml
```

Agora confira os mesmos testes do `checkpoint1.txt` ao vivo:

```bash
# Ver todos os 4 contêineres rodando
sudo docker ps

# Conferir as rotas estáticas nos roteadores
sudo docker exec clab-cafeplanalto-r-matriz ip route
sudo docker exec clab-cafeplanalto-r-filial ip route

# Conferir que o encaminhamento IP (ip_forward) está em 1
sudo docker exec clab-cafeplanalto-r-matriz sysctl net.ipv4.ip_forward
sudo docker exec clab-cafeplanalto-r-filial sysctl net.ipv4.ip_forward

# Pingar da filial (cliente-carga) até a matriz (api 172.20.10.21) -> conferir ttl=62 e 0% loss
sudo docker exec clab-cafeplanalto-cliente-carga ping -c 4 172.20.10.21

# Fazer traceroute da filial até a api -> deve mostrar 172.20.20.1 -> 10.0.0.1 -> 172.20.10.21
sudo docker exec clab-cafeplanalto-cliente-carga traceroute -n 172.20.10.21
```

**Teste extra (comprovar que nada vaza pela `eth0`):**
```bash
# Derruba a interface WAN do r-filial
sudo docker exec clab-cafeplanalto-r-filial ip link set eth1 down

# Ping agora DEVE FALHAR (100% packet loss)
sudo docker exec clab-cafeplanalto-cliente-carga ping -c 2 -W 1 172.20.10.21

# Religa a interface WAN do r-filial
sudo docker exec clab-cafeplanalto-r-filial ip link set eth1 up
```

---

## Etapa 7 — Passo a Passo Prático: Como Unir a Sua API (`app`) com a Infraestrutura (`cafeplanalto`)

Agora vamos substituir o contêiner "oco" (`netlab:1.0`) do nó `api` pela **sua API real da Loja Café Planalto** (`cafeplanalto/api:latest`) dentro da mesma pasta `~/cafeplanalto`!

### Passo 7.1 — Copiar os arquivos da sua API para `~/cafeplanalto/app/`
No terminal **Ubuntu (WSL2)**, dentro de `~/cafeplanalto`:

```bash
# 1. Garante que estamos em ~/cafeplanalto
cd ~/cafeplanalto

# 2. Remove o marcador .gitkeep de app/
rm -f ~/cafeplanalto/app/.gitkeep

# 3. Copia APENAS os arquivos do seu projeto (sem .venv, .agente, .git, PDF ou md de divisão)
cp -r "/mnt/c/Users/jeanj/Projetos/Projeto_E_Administracao_De_Redes/Projeto_Final/app/src" ~/cafeplanalto/app/
cp -r "/mnt/c/Users/jeanj/Projetos/Projeto_E_Administracao_De_Redes/Projeto_Final/app/tests" ~/cafeplanalto/app/
cp "/mnt/c/Users/jeanj/Projetos/Projeto_E_Administracao_De_Redes/Projeto_Final/app/Dockerfile" ~/cafeplanalto/app/
cp "/mnt/c/Users/jeanj/Projetos/Projeto_E_Administracao_De_Redes/Projeto_Final/app/.dockerignore" ~/cafeplanalto/app/
cp "/mnt/c/Users/jeanj/Projetos/Projeto_E_Administracao_De_Redes/Projeto_Final/app/.env.example" ~/cafeplanalto/app/
cp "/mnt/c/Users/jeanj/Projetos/Projeto_E_Administracao_De_Redes/Projeto_Final/app/requirements.txt" ~/cafeplanalto/app/
cp "/mnt/c/Users/jeanj/Projetos/Projeto_E_Administracao_De_Redes/Projeto_Final/app/README.md" ~/cafeplanalto/app/

# 4. Cria o .gitignore na raiz de ~/cafeplanalto para proteger o repositório conjunto no Git
cat << 'EOF' > ~/cafeplanalto/.gitignore
.env
.venv/
.agente/
__pycache__/
*.py[cod]
.pytest_cache/
infra/clab-cafeplanalto/
EOF

# 5. Confere os arquivos copiados em app/
ls -la ~/cafeplanalto/app
```

### Passo 7.2 — Adicionar `curl` em `~/cafeplanalto/infra/Dockerfile`
Para que o nó `cliente-carga` consiga fazer requisições HTTP (`GET` e `POST`) com `curl` para testar sua API, atualize `~/cafeplanalto/infra/Dockerfile`:

```bash
cat << 'EOF' > ~/cafeplanalto/infra/Dockerfile
FROM alpine:3

RUN apk add --no-cache \
    iproute2 \
    iputils \
    traceroute \
    procps \
    curl

CMD ["sh", "-c", "while true; do sleep 3600; done"]
EOF
```

### Passo 7.3 — Trocar a imagem do nó `api` em `~/cafeplanalto/infra/topology.yml`
Abra o arquivo `~/cafeplanalto/infra/topology.yml` com o editor `nano`:

```bash
nano ~/cafeplanalto/infra/topology.yml
```

Localize o bloco `api:` (linhas 39–46) que está assim:
```yaml
    api:
      kind: linux
      image: cafeplanalto/netlab:1.0
      exec:
        - ip link set dev eth1 up
        - ip addr add 172.20.10.21/24 dev eth1
        - ip route add 172.20.0.0/16 via 172.20.10.1
        - ip route add 10.0.0.0/30 via 172.20.10.1
```

Mude **apenas a linha `image:`** e adicione `ports:` (opcional, para você também conseguir abrir `http://localhost:8000/docs` no navegador do Windows):
```yaml
    api:
      kind: linux
      image: cafeplanalto/api:latest
      ports:
        - "8000:8000"
      exec:
        - ip link set dev eth1 up
        - ip addr add 172.20.10.21/24 dev eth1
        - ip route add 172.20.0.0/16 via 172.20.10.1
        - ip route add 10.0.0.0/30 via 172.20.10.1
```

*(Para salvar e sair do `nano`: pressione **`Ctrl + O`**, depois **`Enter`**, e depois **`Ctrl + X`**.)*

> **Por que não precisamos mudar mais nada em `exec:`?**
> Porque o seu `app/Dockerfile` já instala **`iproute2`**! O Containerlab vai subir a sua API FastAPI rodando na porta 8000 e logo em seguida rodar `ip link`, `ip addr` e `ip route` dentro dela sem erro.

### Passo 7.4 — Buildar as duas imagens e subir o ambiente integrado
Dentro de `~/cafeplanalto` no terminal Ubuntu:

```bash
cd ~/cafeplanalto

# 1. Rebuilda a imagem de rede (agora com curl) e constrói a imagem da sua API
sudo docker build -t cafeplanalto/netlab:1.0 ./infra
sudo docker build -t cafeplanalto/api:latest ./app

# 2. Garante que as bridges estão criadas e ligadas
sudo ip link add name sw-servicos type bridge 2>/dev/null || true
sudo ip link set sw-servicos up
sudo ip link add name sw-filial type bridge 2>/dev/null || true
sudo ip link set sw-filial up

# 3. Sobe (ou recria) toda a topologia com --reconfigure
sudo containerlab deploy -t infra/topology.yml --reconfigure
```

### Passo 7.5 — Testar ponta a ponta: a Filial comprando café na Matriz pela WAN!
Agora vamos executar requisições reais saindo de **`cliente-carga` (`172.20.20.20`)**, passando por **`r-filial`**, cruzando o link **WAN (`10.0.0.0/30`)**, passando por **`r-matriz`** até bater na sua **API (`172.20.10.21:8000`)**:

```bash
# 1. Confirmar rota pela WAN até a API
sudo docker exec clab-cafeplanalto-cliente-carga traceroute -n 172.20.10.21

# 2. Checar /health da API a partir da filial (esperado: {"status":"ok","database":"memory"})
sudo docker exec clab-cafeplanalto-cliente-carga curl -s http://172.20.10.21:8000/health

# 3. Listar cafés da API a partir da filial
sudo docker exec clab-cafeplanalto-cliente-carga curl -s http://172.20.10.21:8000/produtos

# 4. Criar um pedido real atravessando os dois roteadores
sudo docker exec clab-cafeplanalto-cliente-carga curl -s -X POST http://172.20.10.21:8000/pedidos \
  -H "Content-Type: application/json" \
  -H "X-Trace-Id: wan-teste-01" \
  -d '{"produto_id": 1, "quantidade": 2, "cliente": "filial-01"}'

# 5. Conferir as métricas Prometheus atualizadas (pedidos_criados_total = 1.0)
sudo docker exec clab-cafeplanalto-cliente-carga curl -s http://172.20.10.21:8000/metrics

# 6. Ler os logs JSON gerados dentro do contêiner da sua API (deve mostrar "trace_id": "wan-teste-01")
sudo docker logs --tail 10 clab-cafeplanalto-api
```

**Teste de queda da WAN integrado:**
```bash
# Derruba a WAN no r-filial
sudo docker exec clab-cafeplanalto-r-filial ip link set eth1 down

# Tenta acessar a API da filial: vai dar erro/timeout (não escapa pela eth0!)
sudo docker exec clab-cafeplanalto-cliente-carga curl -m 2 -i http://172.20.10.21:8000/health

# Enquanto isso, diretamente no seu navegador Windows em http://localhost:8000/health a API continua viva!

# Restaura a WAN
sudo docker exec clab-cafeplanalto-r-filial ip link set eth1 up
```

### Passo 7.6 — Encerrar o laboratório ao finalizar os testes
Quando terminar de testar ou apresentar, desmonte a topologia de forma limpa com:

```bash
cd ~/cafeplanalto
sudo containerlab destroy -t infra/topology.yml --cleanup
```

---

## Etapa 8 — Simulado de Arguição sobre Infraestrutura e Redes (Perguntas e Respostas)

1. **Por que o enlace WAN usa a máscara `/30` (`10.0.0.0/30`) em vez de `/24`?**
   > Porque `/30` reserva 4 endereços: rede (`.0`), broadcast (`.3`) e **exatamente 2 IPs utilizáveis** (`.1` para `r-matriz` e `.2` para `r-filial`), sem desperdiçar endereços IP em um link ponto a ponto.

2. **Para que serve o `sysctl -w net.ipv4.ip_forward=1` nos roteadores?**
   > Liga o encaminhamento de pacotes IP entre interfaces no kernel Linux. Sem ele, `r-matriz` e `r-filial` descartariam qualquer pacote que tente passar da LAN para a WAN e vice-versa.

3. **Qual a diferença entre `sw-servicos` (`kind: bridge`) e `r-matriz` (`kind: linux`)?**
   > `sw-servicos` atua na **Camada 2** (switch): interliga equipamentos da mesma rede local (`172.20.10.0/24`) por endereço MAC. Já `r-matriz` atua na **Camada 3** (roteador): interliga redes diferentes (`10.0.0.0/30` e `172.20.10.0/24`) tomando decisões por endereço IP e rotas.

4. **Por que não podemos deixar o monitoramento ou o tráfego da loja passar pela `eth0` (`172.30.0.0/24`)?**
   > Porque `eth0` (`clab-mgmt`) é a rede de gerência fora de banda que liga todos os contêineres em paralelo. Se o tráfego passasse por ela, quando a WAN (`eth1`) caísse o monitoramento continuaria funcionando por fora e esconderia a falha.

5. **Por que `api` e `cliente-carga` precisam de `ip route add 172.20.0.0/16 via <gateway>`?**
   > Porque cada servidor só conhece automaticamente a sua própria LAN (`/24`). Sem a rota `/16` apontando para o gateway `.1`, o pacote destinado à outra unidade sairia pela rota `default` da `eth0` (`172.30.0.1`). Pela regra de *Longest Prefix Match*, `/16` é mais específico que `/0`, forçando o tráfego para a rede de dados.

6. **Por que o `ping` no `evidencias/checkpoint1.txt` mostrou `ttl=62`?**
   > No Linux o TTL inicial é `64`. Cada roteador subtrai `1` ao encaminhar o pacote. Passando por `r-filial` e `r-matriz` (2 roteadores), o valor final chega como `62`.

7. **No `traceroute` da filial até a API, por que aparecem `172.20.20.1`, `10.0.0.1` e `172.20.10.21` (e não `10.0.0.2`)?**
   > Cada roteador responde ao `traceroute` com o IP da interface por onde o pacote **entrou** nele: `172.20.20.1` é a `eth2` do `r-filial`, `10.0.0.1` é a `eth1` do `r-matriz` e `172.20.10.21` é a `eth1` da `api`.

8. **Qual a diferença entre a Falha 1 (derrubar `eth1` com `ip link set down`) e a Falha 2 (apagar a rota estática com `ip route del`)?**
   > Na Falha 1 a interface física/virtual cai: o estado operacional muda para `DOWN` no SNMP e nenhum pacote passa pela WAN. Na Falha 2 as interfaces continuam `UP` no SNMP, mas o roteador não sabe para onde encaminhar o destino e descarta os pacotes por falta de rota na tabela.
