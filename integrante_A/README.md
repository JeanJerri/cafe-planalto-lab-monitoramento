
# Café Planalto — Monitoramento e Observabilidade

## Checkpoint 1 — Infraestrutura e conectividade

### Ambiente
- Ubuntu via WSL2
- Docker Engine 29.8.1
- Containerlab 0.83.0
- Imagem: cafeplanalto/netlab:1.0

### Topologia implantada
- r-matriz
- r-filial
- sw-servicos
- sw-filial
- api
- cliente-carga

### Redes
- WAN: 10.0.0.0/30
- LAN Serviços: 172.20.10.0/24
- LAN Filial: 172.20.20.0/24
- Gerência: 172.30.0.0/24

### Implantação

Construção da imagem:

```bash
sudo docker build -t cafeplanalto/netlab:1.0 ./infra
```

Inicialização das bridges:

```bash
sudo ip link add name sw-servicos type bridge
sudo ip link set sw-servicos up

sudo ip link add name sw-filial type bridge
sudo ip link set sw-filial up
```

Implantação da topologia:

```bash
sudo containerlab deploy -t infra/topology.yml
```

### Testes de conectividade

Ping:

```bash
sudo docker exec clab-cafeplanalto-cliente-carga ping -c 4 172.20.10.21
```

Traceroute:

```bash
sudo docker exec clab-cafeplanalto-cliente-carga traceroute -n 172.20.10.21
```

### Resultado

Comunicação entre a filial e a LAN Serviços estabelecida.

Traceroute confirmado:

1. 172.20.20.1 — r-filial
2. 10.0.0.1 — r-matriz
3. 172.20.10.21 — api
