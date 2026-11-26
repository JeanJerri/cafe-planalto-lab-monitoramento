### 1. Etapa Zero: Alinhamento e Contratos de Interface (Juntos no Git)
Para que nenhum dos dois fique travado esperando o outro, dediquem o primeiro momento para acordar os "contratos" do ambiente:
* **Repositório Git estruturado**: organizem as pastas (ex.: `/infra`, `/app`, `/zabbix`, `/prometheus-grafana`, `/docs`).
* **Plano de endereçamento IP e nomes fixos**: o roteiro já define rigidamente as sub-redes (WAN `10.0.0.0/30`, Serviços `172.20.10.0/24`, Gerência `172.20.99.0/24`, Filial `172.20.20.0/24` e Gerência fora de banda `172.30.0.0/24`). Seguir à risca esses IPs garante que cada um monte seus arquivos de configuração de forma independente.
* **Padronização das portas e rotas da API**: definam com antecedência os endpoints (`/produtos`, `/pedidos`, `/health`, `/metrics`, `/admin/caos`) e o hostname `loja.cafeplanalto.lab`.

---

### 2. Divisão das Tarefas em Dois Perfis Complementares

#### **Integrante A: Foco em Infraestrutura de Rede, Topologia e Zabbix** *(Visão NetAdmin / SysAdmin)*
Responsável por garantir que a rede física/virtual exista e que a visão tradicional de monitoramento de infraestrutura funcione.
* **Topologia e Conectividade (Containerlab/Linux)**:
  * Montar a topologia no Containerlab com os roteadores Alpine (`r-matriz` e `r-filial`), switches em bridge Linux e o DNS interno (CoreDNS).
  * Configurar o roteamento estático entre matriz e filial e habilitar o encaminhamento IP (`net.ipv4.ip_forward=1`).
  * Garantir a regra de ouro do laboratório: o tráfego de coleta deve atravessar a rede de dados/WAN (eth1 em diante) e nunca a rede fora de banda eth0.
* **Pilha Zabbix (LAN Gerência)**:
  * Subir os contêineres do Zabbix Server, frontend web e banco de dados na LAN Gerência (`172.20.99.10-12`).
  * Configurar agentes Zabbix 2 nos nós da matriz com templates oficiais (Linux, Nginx, PostgreSQL).
  * Implementar monitoramento SNMP v2c com descoberta automática (LLD) das interfaces dos roteadores (tráfego, erros, status operacional).
  * Configurar monitoramento ICMP da WAN e dos hosts da filial.
  * Criar cenário web com 2 passos (catálogo e pedido), triggers com dependências (para evitar alerta em cascata se o roteador da filial cair), mapa de rede e alertas reais (Telegram ou Discord).

#### **Integrante B: Foco em Aplicação, Carga e Observabilidade Moderna** *(Visão SRE / DevOps)*
Responsável pelo ecossistema da aplicação Café Planalto e pela observabilidade focada em métricas de serviço, logs e SLOs.
* **Aplicação e Tráfego Contínuo**:
  * Desenvolver (ou adaptar) a API da loja (FastAPI ou Express) em 3 camadas (Nginx + API + PostgreSQL).
  * Implementar as métricas obrigatórias do Prometheus (`http_requests_total`, histograma de duração, métricas de negócio e pool de conexões do banco) e os endpoints `/health` e `/admin/caos`.
  * Configurar a saída de logs em JSON estruturado.
  * Criar o cliente-carga na filial (k6 ou Locust) gerando tráfego contínuo de 5 a 20 req/s através da WAN.
* **Pilha Prometheus + Grafana + Loki (LAN Gerência)**:
  * Subir Prometheus, Alertmanager, Grafana e Loki na LAN Gerência (`172.20.99.20-23`).
  * Configurar a coleta dos alvos: node_exporter, cAdvisor, postgres_exporter, nginx-exporter e o endpoint da API.
  * Configurar o Blackbox exporter na filial (`172.20.20.30`) medindo HTTP, DNS e ICMP.
  * Provisionar como código os dashboards do Grafana: Infraestrutura (método USE), Aplicação (método RED) e Negócio.
  * Configurar Loki + Promtail/Alloy para receber logs e criar correlação com um clique (do gráfico de erro diretamente para os logs).
  * Definir regras de alerta no Alertmanager e painel com os dois SLOs e orçamento de erro.

---

### 3. Como Manter a Independência no Desenvolvimento Remoto
1. **Mock inicial da aplicação para o Integrante A**: enquanto a API definitiva não estiver pronta, o Integrante A pode usar um simples contêiner Nginx ou um script básico retornando código 200 para validar as rotas, o DNS e o cenário web do Zabbix.
2. **Ambiente local leve para o Integrante B**: o Integrante B pode desenvolver a API e testar os dashboards do Prometheus/Grafana localmente usando Docker Compose tradicional antes de plugar o arquivo de configuração na rede final do Containerlab.
3. **Provisionamento como Código (IaC)**: o trabalho exige que quase nada seja feito apenas "clicando na interface" (sob pena de valer metade dos pontos). Como tudo deve estar em arquivos YAML, JSON ou scripts versionados no Git, vocês integram os módulos através de *pull requests* ou commits sem quebrar a máquina um do outro.

---

### 4. Como Garantir o Domínio Mútuo (Preparação para a Arguição)
Como o professor fará uma **arguição individual cruzada** (perguntando a cada um sobre o que não apresentou) e injetará **2 falhas ao vivo do catálogo**, adotem a seguinte rotina:
* **Sessão semanal de "Demo Cruzada"**: toda semana, façam uma chamada de 30 minutos em que cada um compartilha a tela e ensina ao outro o que implementou e como funciona internamente.
* **Semana 3 dedicada aos Ensaios de Caos**: usem o catálogo de falhas do documento (queda da WAN, perda de rota, latência com `netem`, banco parado, injeção de erro 500 e DNS fora). Injetem as falhas juntos e pratiquem narrar em voz alta o que aparece no Zabbix e o que aparece no Grafana.
* **Escrita Compartilhada do Relatório**: o relatório exige comparar criticamente as duas abordagens (push vs pull, agente vs exporter, alertas de sintoma vs causa, consumo de recursos). Dividam os tópicos do relatório de forma invertida: quem focou no Zabbix escreve sobre os achados de observabilidade da aplicação, e quem focou no Prometheus analisa o comportamento da rede e infraestrutura.
