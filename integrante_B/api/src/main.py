"""Ponto de entrada da API da Loja Café Planalto."""

import asyncio
from contextlib import asynccontextmanager
import logging
import time

from fastapi import Body, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from starlette.routing import Match

from src.chaos import CHAOS_EXEMPT_PATHS, ChaosState
from src.config import Settings, load_settings
from src.logging_json import configure_logging, extract_trace_id
from src.metrics import (
    CONTENT_TYPE_LATEST,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    PEDIDOS_CRIADOS_TOTAL,
    PEDIDOS_VALOR_REAIS_TOTAL,
    generate_latest,
)
from src.models import (
    CaosConfig,
    CaosStatus,
    HealthResponse,
    PedidoCreate,
    PedidoResponse,
    Produto,
)
from src.repository import BaseRepository, DatabaseUnavailableError, create_repository


def resolve_route_path(app: FastAPI, request: Request) -> str:
    """Resolve o template da rota para evitar alta cardinalidade nas métricas."""
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return str(route.path)

    for candidate in app.routes:
        match, _ = candidate.matches(request.scope)
        if match == Match.FULL and getattr(candidate, "path", None):
            return str(candidate.path)

    return "/unmatched"


def create_app(
    repository: BaseRepository | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Cria e configura a instância FastAPI com observabilidade e controle de caos."""
    resolved_settings = settings or load_settings()
    logger = configure_logging(resolved_settings.log_level)
    repo = repository or create_repository(resolved_settings)
    chaos_state = ChaosState()

    @asynccontextmanager
    async def lifespan(fastapi_app: FastAPI):
        fastapi_app.state.repository.initialize()
        logger.info(
            "API Café Planalto inicializada",
            extra={"evento": "startup", "status": 200},
        )
        try:
            yield
        finally:
            fastapi_app.state.repository.close()
            logger.info(
                "API Café Planalto encerrada",
                extra={"evento": "shutdown"},
            )

    app = FastAPI(
        title="Loja Café Planalto API",
        description="API observável da Loja Café Planalto para monitoramento e engenharia de caos.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.repository = repo
    app.state.chaos_state = chaos_state
    app.state.logger = logger

    @app.middleware("http")
    async def observability_and_chaos_middleware(request: Request, call_next):
        inicio = time.perf_counter()
        trace_id = extract_trace_id(request.headers)
        response: Response | None = None

        if request.url.path not in CHAOS_EXEMPT_PATHS:
            latencia_ms = chaos_state.latencia_ms
            if latencia_ms > 0:
                await asyncio.sleep(latencia_ms / 1000.0)
            if chaos_state.should_fail():
                response = JSONResponse(
                    status_code=500,
                    content={"detail": "Erro interno simulado por injeção de caos"},
                )

        if response is None:
            try:
                response = await call_next(request)
            except DatabaseUnavailableError as exc:
                logger.error(
                    "Falha de acesso ao banco de dados",
                    extra={
                        "rota": resolve_route_path(app, request),
                        "metodo": request.method,
                        "status": 503,
                        "trace_id": trace_id,
                        "erro": str(exc),
                    },
                )
                response = JSONResponse(
                    status_code=503,
                    content={"detail": "Banco de dados indisponível"},
                )
            except Exception as exc:  # pragma: no cover - proteção global inesperada
                logger.exception(
                    "Erro não tratado na requisição",
                    extra={
                        "rota": resolve_route_path(app, request),
                        "metodo": request.method,
                        "status": 500,
                        "trace_id": trace_id,
                        "erro": str(exc),
                    },
                )
                response = JSONResponse(
                    status_code=500,
                    content={"detail": "Erro interno no servidor"},
                )

        duracao_s = time.perf_counter() - inicio
        duracao_ms = round(duracao_s * 1000.0, 2)
        rota = resolve_route_path(app, request)

        if rota != "/metrics":
            HTTP_REQUESTS_TOTAL.labels(
                rota=rota,
                metodo=request.method,
                status=str(response.status_code),
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(rota=rota).observe(duracao_s)

            if response.status_code >= 500:
                nivel = logging.ERROR
            elif response.status_code >= 400:
                nivel = logging.WARNING
            else:
                nivel = logging.INFO

            logger.log(
                nivel,
                "Requisição HTTP processada",
                extra={
                    "rota": rota,
                    "metodo": request.method,
                    "status": response.status_code,
                    "duracao_ms": duracao_ms,
                    "trace_id": trace_id,
                },
            )

        return response

    @app.get("/", summary="Informações da API")
    def read_root() -> dict[str, object]:
        return {
            "servico": "Loja Café Planalto API",
            "versao": "0.1.0",
            "rotas": [
                "GET /produtos",
                "POST /pedidos",
                "GET /pedidos",
                "GET /health",
                "GET /metrics",
                "GET /admin/caos",
                "POST /admin/caos",
            ],
        }

    @app.get("/produtos", response_model=list[Produto], summary="Lista catálogo de cafés")
    def listar_produtos(request: Request) -> list[Produto]:
        produtos = request.app.state.repository.list_produtos()
        return [Produto(**item) for item in produtos]

    @app.post(
        "/pedidos",
        response_model=PedidoResponse,
        status_code=201,
        summary="Cria um novo pedido na loja",
    )
    def criar_pedido(payload: PedidoCreate, request: Request) -> PedidoResponse:
        pedido = request.app.state.repository.create_pedido(
            produto_id=payload.produto_id,
            quantidade=payload.quantidade,
            cliente=payload.cliente,
        )
        if pedido is None:
            raise HTTPException(status_code=404, detail="Produto não encontrado")

        PEDIDOS_CRIADOS_TOTAL.inc()
        PEDIDOS_VALOR_REAIS_TOTAL.inc(pedido["valor_total_reais"])

        trace_id = extract_trace_id(request.headers)
        logger.info(
            "Pedido criado com sucesso",
            extra={
                "evento": "pedido_criado",
                "rota": "/pedidos",
                "metodo": "POST",
                "status": 201,
                "pedido_id": pedido["id"],
                "produto_id": pedido["produto_id"],
                "valor_total_reais": pedido["valor_total_reais"],
                "trace_id": trace_id,
            },
        )
        return PedidoResponse(**pedido)

    @app.get("/pedidos", response_model=list[PedidoResponse], summary="Lista pedidos criados")
    def listar_pedidos(request: Request) -> list[PedidoResponse]:
        pedidos = request.app.state.repository.list_pedidos()
        return [PedidoResponse(**item) for item in pedidos]

    @app.get(
        "/health",
        response_model=HealthResponse,
        summary="Verifica saúde da API e do banco de dados",
    )
    def healthcheck(request: Request):
        ok, backend = request.app.state.repository.check_health()
        if ok:
            return HealthResponse(status="ok", database=backend)

        logger.error(
            "Healthcheck falhou: banco de dados indisponível",
            extra={
                "evento": "healthcheck_falhou",
                "rota": "/health",
                "metodo": "GET",
                "status": 503,
                "trace_id": extract_trace_id(request.headers),
            },
        )
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": backend},
        )

    @app.get("/metrics", summary="Expõe métricas no formato Prometheus")
    def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/admin/caos", response_model=CaosStatus, summary="Consulta estado atual do caos")
    def status_caos(request: Request) -> CaosStatus:
        return CaosStatus(**request.app.state.chaos_state.snapshot())

    @app.post("/admin/caos", response_model=CaosStatus, summary="Configura injeção de caos")
    def configurar_caos(
        request: Request,
        payload: CaosConfig | None = Body(default=None),
        latencia_ms: int | None = Query(default=None, ge=0, le=30000),
        taxa_erro: float | None = Query(default=None, ge=0.0, le=1.0),
    ) -> CaosStatus:
        resolved_latencia = latencia_ms if latencia_ms is not None else (payload.latencia_ms if payload else None)
        resolved_taxa = taxa_erro if taxa_erro is not None else (payload.taxa_erro if payload else None)

        estado = request.app.state.chaos_state.update(
            latencia_ms=resolved_latencia,
            taxa_erro=resolved_taxa,
        )
        logger.warning(
            "Configuração de caos atualizada",
            extra={
                "evento": "caos_atualizado",
                "rota": "/admin/caos",
                "metodo": "POST",
                "status": 200,
                "trace_id": extract_trace_id(request.headers),
            },
        )
        return CaosStatus(**estado)

    return app


app = create_app()
