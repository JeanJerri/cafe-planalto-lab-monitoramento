"""Definição das métricas Prometheus obrigatórias da Loja Café Planalto."""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

# Regra de cardinalidade: usar apenas labels de domínio limitado (rota, metodo, status).
# Nunca adicionar pedido_id, cliente ou URL bruta como label no Prometheus.

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total de requisições HTTP processadas pela API",
    ["rota", "metodo", "status"],
)

# Buckets cobrem latências típicas (5ms-300ms) até o cenário de caos (800ms+).
# O bucket 0.3s corresponde diretamente ao SLO de p95 < 300ms sugerido no roteiro.
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Duração das requisições HTTP em segundos por rota",
    ["rota"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 2.5, 5.0),
)

PEDIDOS_CRIADOS_TOTAL = Counter(
    "pedidos_criados_total",
    "Total acumulado de pedidos criados na Loja Café Planalto",
)

PEDIDOS_VALOR_REAIS_TOTAL = Counter(
    "pedidos_valor_reais_total",
    "Valor total acumulado em reais (BRL) dos pedidos criados",
)

DB_POOL_CONEXOES_EM_USO = Gauge(
    "db_pool_conexoes_em_uso",
    "Número atual de conexões em uso no pool do banco de dados",
)

__all__ = [
    "CONTENT_TYPE_LATEST",
    "DB_POOL_CONEXOES_EM_USO",
    "HTTP_REQUEST_DURATION_SECONDS",
    "HTTP_REQUESTS_TOTAL",
    "PEDIDOS_CRIADOS_TOTAL",
    "PEDIDOS_VALOR_REAIS_TOTAL",
    "generate_latest",
]
