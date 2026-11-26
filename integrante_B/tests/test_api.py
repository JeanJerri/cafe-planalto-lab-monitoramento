"""Testes automatizados da API da Loja Café Planalto."""

import io
import json
import logging
import time

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY
from prometheus_client.parser import text_string_to_metric_families

from src.logging_json import JsonFormatter, extract_trace_id
from src.main import create_app
from src.repository import DatabaseUnavailableError, InMemoryRepository


class FailingHealthRepository(InMemoryRepository):
    """Repositório simulando indisponibilidade do banco de dados."""

    def check_health(self) -> tuple[bool, str]:
        return False, "unavailable"

    def list_produtos(self) -> list[dict]:
        raise DatabaseUnavailableError("Banco offline")


def _sample(metric_name: str, labels: dict[str, str] | None = None) -> float:
    value = REGISTRY.get_sample_value(metric_name, labels or {})
    return float(value) if value is not None else 0.0


def test_endpoints_catalogo_e_pedidos():
    app = create_app(repository=InMemoryRepository())
    with TestClient(app) as client:
        root_resp = client.get("/")
        assert root_resp.status_code == 200
        assert "rotas" in root_resp.json()

        prod_resp = client.get("/produtos")
        assert prod_resp.status_code == 200
        produtos = prod_resp.json()
        assert len(produtos) == 5
        primeiro = produtos[0]

        pedido_resp = client.post(
            "/pedidos",
            json={"produto_id": primeiro["id"], "quantidade": 2, "cliente": "teste-filial"},
        )
        assert pedido_resp.status_code == 201
        pedido = pedido_resp.json()
        assert pedido["produto_id"] == primeiro["id"]
        assert pedido["quantidade"] == 2
        assert pedido["valor_total_reais"] == round(primeiro["preco_reais"] * 2, 2)
        assert pedido["status"] == "confirmado"

        lista_resp = client.get("/pedidos")
        assert lista_resp.status_code == 200
        assert len(lista_resp.json()) == 1

        not_found_resp = client.post(
            "/pedidos",
            json={"produto_id": 9999, "quantidade": 1},
        )
        assert not_found_resp.status_code == 404


def test_health_saudavel_e_indisponivel():
    app_ok = create_app(repository=InMemoryRepository())
    with TestClient(app_ok) as client_ok:
        resp_ok = client_ok.get("/health")
        assert resp_ok.status_code == 200
        assert resp_ok.json() == {"status": "ok", "database": "memory"}

    app_down = create_app(repository=FailingHealthRepository())
    with TestClient(app_down) as client_down:
        resp_health = client_down.get("/health")
        assert resp_health.status_code == 503
        assert resp_health.json()["status"] == "error"

        resp_produtos = client_down.get("/produtos")
        assert resp_produtos.status_code == 503


def test_metricas_prometheus_obrigatorias_e_cardinalidade():
    app = create_app(repository=InMemoryRepository())
    with TestClient(app) as client:
        pedidos_antes = _sample("pedidos_criados_total")
        valor_antes = _sample("pedidos_valor_reais_total")
        req_prod_antes = _sample(
            "http_requests_total",
            {"rota": "/produtos", "metodo": "GET", "status": "200"},
        )

        produtos = client.get("/produtos").json()
        preco = produtos[1]["preco_reais"]
        resp_pedido = client.post(
            "/pedidos",
            json={"produto_id": produtos[1]["id"], "quantidade": 3, "cliente": "cliente-vip-99"},
        )
        assert resp_pedido.status_code == 201

        metrics_resp = client.get("/metrics")
        assert metrics_resp.status_code == 200
        body = metrics_resp.text

        samples_by_name: dict[str, list[tuple[dict[str, str], float]]] = {}
        for family in text_string_to_metric_families(body):
            for sample in family.samples:
                samples_by_name.setdefault(sample.name, []).append((sample.labels, sample.value))

        assert any(
            labels == {"rota": "/produtos", "metodo": "GET", "status": "200"}
            for labels, _ in samples_by_name.get("http_requests_total", [])
        )
        assert any(
            labels == {"le": "0.3", "rota": "/produtos"}
            for labels, _ in samples_by_name.get("http_request_duration_seconds_bucket", [])
        )
        assert any(
            labels == {"rota": "/produtos"}
            for labels, _ in samples_by_name.get("http_request_duration_seconds_count", [])
        )
        assert any(
            labels == {"rota": "/produtos"}
            for labels, _ in samples_by_name.get("http_request_duration_seconds_sum", [])
        )
        assert "pedidos_criados_total" in samples_by_name
        assert "pedidos_valor_reais_total" in samples_by_name
        assert "db_pool_conexoes_em_uso" in samples_by_name

        assert "_total_total" not in body
        assert "pedido_id=" not in body
        assert "cliente=" not in body

        assert _sample("pedidos_criados_total") == pedidos_antes + 1
        assert _sample("pedidos_valor_reais_total") == pytest.approx(valor_antes + preco * 3, rel=1e-6)
        assert (
            _sample(
                "http_requests_total",
                {"rota": "/produtos", "metodo": "GET", "status": "200"},
            )
            == req_prod_antes + 1
        )


def test_injecao_de_caos_e_rotas_imunes():
    app = create_app(repository=InMemoryRepository())
    with TestClient(app) as client:
        err_500_antes = _sample(
            "http_requests_total",
            {"rota": "/produtos", "metodo": "GET", "status": "500"},
        )

        # Ativa 100% de erro 500 via JSON
        caos_resp = client.post("/admin/caos", json={"taxa_erro": 1.0, "latencia_ms": 0})
        assert caos_resp.status_code == 200
        assert caos_resp.json() == {"latencia_ms": 0, "taxa_erro": 1.0, "ativo": True}

        assert client.get("/produtos").status_code == 500
        assert (
            _sample(
                "http_requests_total",
                {"rota": "/produtos", "metodo": "GET", "status": "500"},
            )
            == err_500_antes + 1
        )

        # Rotas administrativas/observabilidade permanecem imunes
        assert client.get("/health").status_code == 200
        assert client.get("/metrics").status_code == 200
        assert client.get("/admin/caos").status_code == 200

        # Testa atraso artificial de 150ms
        lat_resp = client.post("/admin/caos", json={"taxa_erro": 0.0, "latencia_ms": 150})
        assert lat_resp.status_code == 200

        t0 = time.perf_counter()
        ok_resp = client.get("/produtos")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert ok_resp.status_code == 200
        assert elapsed_ms >= 135.0

        # Desliga caos via query params e confirma retorno normal
        reset_resp = client.post("/admin/caos?latencia_ms=0&taxa_erro=0")
        assert reset_resp.status_code == 200
        assert reset_resp.json() == {"latencia_ms": 0, "taxa_erro": 0.0, "ativo": False}
        assert client.get("/produtos").status_code == 200


def test_logs_json_estruturados_e_trace_id():
    app = create_app(repository=InMemoryRepository())
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    app.state.logger.addHandler(handler)

    try:
        with TestClient(app) as client:
            resp_sem_trace = client.get("/produtos")
            assert resp_sem_trace.status_code == 200

            resp_com_trace = client.get(
                "/produtos",
                headers={"X-Trace-Id": "trace-abc-123"},
            )
            assert resp_com_trace.status_code == 200

            traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
            resp_w3c = client.get(
                "/produtos",
                headers={"traceparent": traceparent},
            )
            assert resp_w3c.status_code == 200
    finally:
        app.state.logger.removeHandler(handler)

    linhas = [json.loads(line) for line in stream.getvalue().strip().splitlines() if line.strip()]
    logs_produtos = [entry for entry in linhas if entry.get("rota") == "/produtos"]
    assert len(logs_produtos) == 3

    sem_trace, com_x_trace, com_w3c = logs_produtos
    for entry in logs_produtos:
        assert entry["timestamp"].endswith("Z")
        assert entry["nivel"] == "INFO"
        assert entry["rota"] == "/produtos"
        assert entry["status"] == 200
        assert isinstance(entry["duracao_ms"], float)

    assert "trace_id" not in sem_trace
    assert com_x_trace["trace_id"] == "trace-abc-123"
    assert com_w3c["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert extract_trace_id({"traceparent": "invalid"}) is None
