# Guia Passo a Passo — Execução, Configuração e Testes (Do Zero)

Este documento reúne **todos os comandos práticos** para configurar, subir, testar manualmente e validar o projeto **Café Planalto** no **Windows + WSL2** (mantendo compatibilidade total com Linux nativo / VM Ubuntu).

> **Quer entender a teoria por trás de cada ferramenta?** Consulte os módulos curtos em [`docs/estudo/README.md`](estudo/README.md).

---

## 1. Preparação Inicial no Windows + WSL2 (Do Zero)

### 1.1 Abrir o Ubuntu (WSL2) e conferir ferramentas
1. Pressione a tecla **Windows**, digite **`Ubuntu`** e abra o terminal do Ubuntu (ou abra o PowerShell e digite `wsl`).
2. Verifique se **Docker**, **Docker Compose** e **Containerlab** estão instalados:
   ```bash
   docker --version
   docker compose version
   containerlab version
   ```
3. Se o **Docker** não responder dentro do WSL2, abra o **Docker Desktop** no Windows, vá em *Settings → Resources → WSL Integration* e ative a integração para o seu **Ubuntu**.
4. Se o **`containerlab`** der *command not found* (necessário apenas na Seção 4), instale com:
   ```bash
   curl -sL https://containerlab.dev/setup | sudo -E bash -s "all"
   ```

### 1.2 Trabalhar na pasta Linux do WSL (`~/Projeto_Final`)
No WSL2, o disco `C:\` do Windows aparece em `/mnt/c/...`, que é mais lento e pode causar problemas de permissão em bancos de dados. Trabalhe dentro da sua home Linux (`~`):
```bash
# Se ainda não clonou direto no WSL, copie ou clone na sua home Linux:
cd ~
git clone https://github.com/JeanJerri/cafe-planalto-lab-monitoramento.git Projeto_Final
cd ~/Projeto_Final
```
*(Se já tiver o projeto no Windows e quiser copiar as alterações locais sem clonar do zero: `cp -r /mnt/c/Users/jeanj/Projetos/Projeto_E_Administracao_De_Redes/Projeto_Final ~/Projeto_Final`.)*

### 1.3 Sincronizar o relógio do WSL2 (quando necessário)
Se o notebook hibernou no Windows, o relógio do WSL2 pode atrasar e bagunçar gráficos/alertas. Para sincronizar:
```bash
sudo hwclock -s
date
```

---

## 2. Configurar o `.env` da Parte B (E-mail do Alertmanager)

O arquivo `.env` fica **apenas no seu computador** (ignorado pelo `.gitignore`).

### Passo 2.1 — Gerar uma Senha de App no Gmail
1. Entre na sua conta Google e ative a **Verificação em duas etapas** (se ainda não estiver ativa).
2. Vá em **Gerenciar sua Conta Google → Segurança → Senhas de app**.
3. Crie uma senha com o nome `CafePlanalto` e copie os **16 caracteres** gerados (remova espaços, ex.: `abcdabcdabcdabcd`).

### Passo 2.2 — Criar e preencher `integrante_B/.env`
```bash
cd ~/Projeto_Final/integrante_B
cp .env.example .env
nano .env
```
Preencha pelo menos estas 6 linhas de e-mail (as outras podem ficar em branco para usar os valores padrão):
```env
SMTP_SMARTHOST=smtp.gmail.com:587
SMTP_FROM=seu.email@gmail.com
SMTP_AUTH_USERNAME=seu.email@gmail.com
SMTP_AUTH_PASSWORD=abcdabcdabcdabcd
SMTP_REQUIRE_TLS=true
ALERT_EMAIL_TO=seu.email@gmail.com
```
*(No `nano`: salve com **`Ctrl + O`**, **`Enter`**, e saia com **`Ctrl + X`**.)*

---

## 3. Executar e Testar a Parte B (Aplicação, Carga, Exporters, Prometheus e Alertmanager)

### Passo 3.1 — Subir toda a stack local
```bash
cd ~/Projeto_Final/integrante_B
docker compose up -d --build
docker compose ps
```
**O que deve aparecer:** os **12 contêineres** no estado `Up` (`cafeplanalto-dev-db` deve estar `healthy`).

### Passo 3.2 — Validar sintaxe via CLI
```bash
docker exec cafeplanalto-dev-prometheus promtool check config /etc/prometheus/prometheus.yml
docker exec cafeplanalto-dev-prometheus promtool check rules /etc/prometheus/rules/alerts.yml
docker exec cafeplanalto-dev-alertmanager amtool check-config /tmp/alertmanager.yml
```
**Esperado:** os 3 comandos retornam **`SUCCESS`**.

### Passo 3.3 — URLs para abrir no navegador do Windows
*(O WSL2 encaminha `localhost` automaticamente para o Windows.)*

| Serviço | URL | O que conferir |
| --- | --- | --- |
| **Loja Café Planalto (Nginx)** | `http://localhost:8088` | Catálogo de 5 cafés, badge `Saúde: ok (postgres)` e botão comprar |
| **Nginx `stub_status`** | `http://localhost:8089/nginx_status` | Contadores de conexões ativas e requisições |
| **API Swagger / Métricas** | `http://localhost:8000/docs` e `http://localhost:8000/metrics` | Endpoints interativos e métricas Prometheus brutas |
| **Prometheus — Alvos** | `http://localhost:9090/targets` | Os 10 grupos em estado verde **`UP`** |
| **Prometheus — Gráficos/Consultas** | `http://localhost:9090/graph` | Consultas PromQL (`probe_success`, `up`, `rate(...)`) |
| **Prometheus — Alertas** | `http://localhost:9090/alerts` | Regras nos estados `Inactive`, `Pending` e `Firing` |
| **Alertmanager** | `http://localhost:9093` | Alertas ativos agrupados e histórico de silêncios |
| **Blackbox Exporter (`sonda`)** | `http://localhost:9115` | Interface e logs da última sonda executada |
| **cAdvisor** | `http://localhost:8085` | Métricas de CPU e RAM por contêiner |

---

### Passo 3.4 — Checklist de Testes Manuais (Visando os Itens da Apresentação)

#### A) Aplicação em 3 camadas, Logs JSON e Carga (Barema A1, A2, A3)
1. **A1 (Loja funcionando):** abra `http://localhost:8088`, clique em **"Comprar 1 unidade"** e confira a mensagem verde de pedido confirmado (`#ID`). Pelo terminal:
   ```bash
   curl -i http://localhost:8088/health
   curl -s -X POST http://localhost:8088/pedidos \
     -H "Content-Type: application/json" \
     -H "X-Trace-Id: teste-manual-01" \
     -d '{"produto_id": 1, "quantidade": 2, "cliente": "filial-manual"}'
   ```
2. **A2 (Métricas e logs JSON):**
   ```bash
   curl -s http://localhost:8000/metrics | grep -E "http_requests_total|http_request_duration_seconds_bucket|pedidos_|db_pool"
   docker logs --tail 5 cafeplanalto-dev-web
   docker logs --tail 5 cafeplanalto-dev-api
   ```
   *Esperado:* linhas JSON válidas com `timestamp`, `nivel`, `rota`, `status`, `duracao_ms` e `trace_id`.
3. **A3 (Carga contínua k6):**
   ```bash
   docker logs --tail 10 cafeplanalto-dev-loadgen
   ```
   *Esperado:* k6 enviando ~10 req/s sem parar.

#### B) Prometheus — Alvos de coleta (Barema P1 — 5 pontos)
1. Abra **`http://localhost:9090/targets`**.
2. Confirme que **todos os 10 jobs** estão verdes (**`UP`**): `api`, `blackbox_dns`, `blackbox_exporter`, `blackbox_http`, `blackbox_icmp`, `cadvisor`, `nginx_exporter`, `node_exporter`, `postgres_exporter`, `prometheus`.

#### C) Blackbox Exporter — Sondas HTTP, DNS e ICMP (Barema P2 — 4 pontos)
1. Abra **`http://localhost:9090/graph`**, selecione a aba **Table** e execute:
   ```promql
   probe_success
   ```
   *Esperado:* todas as séries (`blackbox_http`, `blackbox_dns` e `blackbox_icmp`) retornando valor **`1`**.
2. Consulte também a latência medida pela sonda HTTP:
   ```promql
   probe_duration_seconds{job="blackbox_http"}
   ```
3. *(Opcional)* Teste direto na porta da sonda:
   ```bash
   curl -s "http://localhost:9115/probe?target=http://web/produtos&module=http_2xx" | grep probe_success
   curl -s "http://localhost:9115/probe?target=dns:53&module=dns_cafeplanalto" | grep probe_success
   ```

#### D) Alertas, Notificação Real por E-mail e Auto-resolução (Barema P3 — 5 pontos + Ensaios de Falhas)
Mantenha abertas as abas **`http://localhost:9090/alerts`** e **`http://localhost:9093`**.

1. **Falha 6 — Erros 500 na API (`/admin/caos`):**
   ```bash
   # Ligar 20% de erro HTTP 500
   curl -s -X POST http://localhost:8088/admin/caos \
     -H "Content-Type: application/json" \
     -d '{"latencia_ms": 0, "taxa_erro": 0.2}'
   ```
   - **Observar:** após ~20–35s, `TaxaDeErros5xxAlta` passa de `Pending` → **`Firing`** no Prometheus, aparece agrupado em `:9093`, e chega no seu celular o e-mail **`[Cafe Planalto][FIRING] TaxaDeErros5xxAlta (critical)`**.
   - **Desligar e validar auto-resolução:**
     ```bash
     curl -s -X POST "http://localhost:8088/admin/caos?latencia_ms=0&taxa_erro=0"
     ```
     Aguarde ~1–2 minutos: o alerta sai de `Firing` e você recebe o e-mail **`[Cafe Planalto][RESOLVED] TaxaDeErros5xxAlta`**.

2. **Falha 4 — Banco de dados parado (`docker stop`):**
   ```bash
   docker stop cafeplanalto-dev-db
   curl -i http://localhost:8088/health   # Esperado: HTTP 503
   ```
   - **Observar:** `BancoPostgreSQLFora` (`pg_up == 0`) e `LojaIndisponivelHTTP` entram em `Firing`.
   - **Recuperar:**
     ```bash
     docker start cafeplanalto-dev-db
     sleep 3
     curl -i http://localhost:8088/health   # Esperado: volta a HTTP 200 sem reiniciar a API
     ```

3. **Falha 5 — API lenta (`latencia_ms=800`):**
   ```bash
   curl -s -X POST http://localhost:8088/admin/caos \
     -H "Content-Type: application/json" \
     -d '{"latencia_ms": 800, "taxa_erro": 0.0}'
   ```
   - **Observar:** `LatenciaP95AcimaDoSLO` e `LatenciaAltaSondaHTTP` passam de `0.3s` e entram em `Firing` (enquanto `/health` continua `200`). Desligue em seguida:
     ```bash
     curl -s -X POST "http://localhost:8088/admin/caos?latencia_ms=0&taxa_erro=0"
     ```

4. **Falha 7 — DNS interno parado:**
   ```bash
   docker stop cafeplanalto-dev-dns
   ```
   - **Observar:** `probe_success{job="blackbox_dns"}` cai para **`0`** e dispara `DNSInternoFalhando`. Religue:
     ```bash
     docker start cafeplanalto-dev-dns
     ```

### Passo 3.5 — Testes automatizados (`pytest`) e encerramento
```bash
cd ~/Projeto_Final/integrante_B

# No Ubuntu 24.04 (WSL2), instale o pacote de ambiente virtual na primeira vez:
sudo apt update && sudo apt install -y python3-venv

# Caso uma tentativa anterior tenha criado uma .venv quebrada, limpe e recrie:
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt pytest httpx
pytest -v api/tests observability/tests
# Esperado: 14 passed
```
Para encerrar os contêineres da Parte B (adicione `-v` apenas se quiser zerar o banco e o histórico do Prometheus):
```bash
docker compose down
```

### Solução rápida de problemas (Parte B)
- **E-mail não chegou:** confira os logs com `docker logs --tail 25 cafeplanalto-dev-alertmanager`. Se deu erro de login SMTP, confira se a Senha de App tem 16 letras **sem espaços** no `.env` e reinicie só o Alertmanager: `docker compose up -d --force-recreate alertmanager`.
- **Conflito de porta `8080`:** no Compose local da Parte B nenhuma porta usa `8080` (`web` usa `8088` e `cadvisor` usa `8085`). Se alguma outra porta estiver ocupada, ajuste no `.env`.

---

## 4. Executar e Testar a Parte A (Containerlab, Rotas, CoreDNS, SNMP e Zabbix)

> **Dica de memória:** se estiver em um notebook com 8 GB de RAM, rode `docker compose down` em `integrante_B/` antes de subir a topologia da Parte A.

### Passo 4.1 — Conferir arquivos locais ignorados em `integrante_A/`
Por segurança, o `.gitignore` não sobe senhas para o GitHub. Se você acabou de fazer um `git clone`, crie os arquivos abaixo em `~/Projeto_Final/integrante_A/` *(se já existirem na sua máquina, pule para o Passo 4.2)*:
- `integrante_A/zabbix/.env`:
  ```env
  POSTGRES_PASSWORD=defina_uma_senha_segura
  ```
- `integrante_A/snmp/.community`: uma linha com a *community* SNMP combinada pela dupla.
- `integrante_A/snmp/snmpd-matriz.conf`:
  ```conf
  agentaddress udp:172.20.99.1:161
  rocommunity SUA_COMMUNITY 172.20.99.0/24
  sysLocation Matriz - Cafe Planalto
  sysContact Equipe de Infraestrutura
  sysName r-matriz
  ```
- `integrante_A/snmp/snmpd-filial.conf`:
  ```conf
  agentaddress udp:10.0.0.2:161
  rocommunity SUA_COMMUNITY 172.20.99.0/24
  sysLocation Filial - Cafe Planalto
  sysContact Equipe de Infraestrutura
  sysName r-filial
  ```

### Passo 4.2 — Build das imagens e subida da topologia Containerlab
*(Atenção: o `topology.yml` usa a tag `:1.1` nos roteadores e `:1.0` nos hosts, por isso passamos os dois `-t` no build.)*
```bash
cd ~/Projeto_Final/integrante_A

# 1. Construir imagens de rede/SNMP e CoreDNS
sudo docker build -t cafeplanalto/netlab:1.1 -t cafeplanalto/netlab:1.0 ./infra
sudo docker build -f infra/Dockerfile.dns -t cafeplanalto/coredns:1.0 ./infra

# 2. Criar e subir as 3 bridges Linux
for br in sw-servicos sw-filial sw-gerencia; do
  sudo ip link add name "$br" type bridge 2>/dev/null || true
  sudo ip link set "$br" up
done

# 3. Subir a topologia no Containerlab
sudo containerlab deploy -t infra/topology.yml
```

### Passo 4.3 — Checklist de Testes Manuais da Parte A
1. **Rotas estáticas e `ip_forward=1` (Barema I1):**
   ```bash
   sudo docker exec clab-cafeplanalto-r-matriz ip route
   sudo docker exec clab-cafeplanalto-r-filial ip route
   sudo docker exec clab-cafeplanalto-r-matriz sysctl net.ipv4.ip_forward
   sudo docker exec clab-cafeplanalto-r-filial sysctl net.ipv4.ip_forward
   ```
2. **Ping (`ttl=62`) e `traceroute` da Filial até a Matriz (Barema I1):**
   ```bash
   sudo docker exec clab-cafeplanalto-cliente-carga ping -c 4 172.20.10.21
   sudo docker exec clab-cafeplanalto-cliente-carga traceroute -n 172.20.10.21
   # Esperado: 172.20.20.1 (r-filial) -> 10.0.0.1 (r-matriz) -> 172.20.10.21 (api)
   ```
3. **DNS interno `cafeplanalto.lab` (Barema I2):**
   ```bash
   sudo docker exec clab-cafeplanalto-dns dig @172.20.10.10 loja.cafeplanalto.lab +short
   # Esperado: 172.20.10.20
   ```
4. **SNMP v2c em `r-matriz` e `r-filial` pela WAN (Barema Z3):**
   ```bash
   COMMUNITY=$(cat snmp/.community)
   sudo docker exec clab-cafeplanalto-host-gerencia snmpwalk -v2c -c "$COMMUNITY" 172.20.99.1 system
   sudo docker exec clab-cafeplanalto-host-gerencia snmpwalk -v2c -c "$COMMUNITY" 10.0.0.2 system
   ```
5. **Falha 1 (Queda da WAN) + Prova da Regra de Ouro (`eth0`):**
   ```bash
   sudo docker exec clab-cafeplanalto-r-filial ip link set eth1 down
   sudo docker exec clab-cafeplanalto-cliente-carga ping -c 2 -W 1 172.20.10.21                         # Deve dar 100% loss
   sudo docker exec clab-cafeplanalto-host-gerencia snmpget -v2c -c "$COMMUNITY" -t 2 -r 1 10.0.0.2 sysName.0  # Deve dar timeout
   sudo docker exec clab-cafeplanalto-r-filial ip link set eth1 up
   ```
6. **Teste de suporte ao `tc netem` no WSL2 (Falha 3):**
   ```bash
   sudo docker exec clab-cafeplanalto-r-filial tc qdisc add dev eth1 root netem delay 300ms loss 5%
   sudo docker exec clab-cafeplanalto-r-filial tc qdisc del dev eth1 root
   ```
   *(Se o primeiro comando der `Operation not supported` ou `No such file`, significa que o kernel do seu WSL2 não traz o módulo `sch_netem` habilitado.)*

### Passo 4.4 — Desmontar o Containerlab e testar a interface do Zabbix (`:8080`)
Antes da integração final (Fase 4), a pilha Zabbix da Integrante A usa uma rede Docker própria na faixa `172.20.99.0/24`; por isso, desmonte o Containerlab antes de subir o Zabbix:
```bash
cd ~/Projeto_Final/integrante_A
sudo containerlab destroy -t infra/topology.yml --cleanup

cd ~/Projeto_Final/integrante_A/zabbix
docker network create --subnet=172.20.99.0/24 zabbix-gerencia 2>/dev/null || true
docker network create zabbix-acesso 2>/dev/null || true
docker compose up -d
docker compose ps
```
- Abra **`http://127.0.0.1:8080`** no navegador (usuário padrão: `Admin` / senha padrão: `zabbix`).
- Para encerrar o Zabbix:
  ```bash
  docker compose down
  ```
