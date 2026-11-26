"""Configuração de logs estruturados em JSON para saída padrão (stdout)."""

from collections.abc import Mapping
from datetime import datetime, timezone
import json
import logging
import sys

STRUCTURED_FIELDS = (
    "rota",
    "metodo",
    "status",
    "duracao_ms",
    "trace_id",
    "pedido_id",
    "produto_id",
    "valor_total_reais",
    "erro",
    "evento",
)


class JsonFormatter(logging.Formatter):
    """Formata registros de log como uma linha JSON por evento."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = (
            datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        payload: dict[str, object] = {
            "timestamp": timestamp,
            "nivel": record.levelname,
            "mensagem": record.getMessage(),
        }

        for field in STRUCTURED_FIELDS:
            value = record.__dict__.get(field)
            if value is None:
                continue
            if field == "trace_id" and not str(value).strip():
                continue
            payload[field] = value

        if record.exc_info and "erro" not in payload:
            payload["erro"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def _get_header_ci(headers: Mapping[str, str], target: str) -> str | None:
    target_lower = target.lower()
    for key, value in headers.items():
        if key.lower() == target_lower:
            return value
    return None


def extract_trace_id(headers: Mapping[str, str]) -> str | None:
    """Extrai trace_id de cabeçalhos W3C traceparent ou X-Trace-Id."""
    traceparent = _get_header_ci(headers, "traceparent")
    if traceparent:
        parts = traceparent.strip().split("-")
        if len(parts) >= 4 and len(parts[1]) == 32 and set(parts[1]) != {"0"}:
            return parts[1].lower()

    x_trace_id = _get_header_ci(headers, "x-trace-id")
    if x_trace_id and x_trace_id.strip():
        return x_trace_id.strip()

    return None


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configura loggers da aplicação e do Uvicorn para emitirem JSON no stdout."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    app_logger = logging.getLogger("cafeplanalto")
    app_logger.handlers.clear()
    app_logger.addHandler(handler)
    app_logger.setLevel(numeric_level)
    app_logger.propagate = False

    for uvicorn_name in ("uvicorn", "uvicorn.error"):
        uv_logger = logging.getLogger(uvicorn_name)
        uv_logger.handlers.clear()
        uv_logger.addHandler(handler)
        uv_logger.setLevel(numeric_level)
        uv_logger.propagate = False

    # O middleware da API já emite logs estruturados de requisição HTTP;
    # desabilitar uvicorn.access evita linhas duplicadas em texto puro.
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = False
    access_logger.disabled = True

    return app_logger
