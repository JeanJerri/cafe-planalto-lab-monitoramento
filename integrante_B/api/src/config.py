"""Configurações da aplicação carregadas a partir de variáveis de ambiente."""

from dataclasses import dataclass
import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback caso python-dotenv não esteja instalado
    def load_dotenv(*_args, **_kwargs) -> bool:
        return False


@dataclass(frozen=True)
class Settings:
    """Parâmetros de execução da API Café Planalto."""

    app_host: str
    app_port: int
    log_level: str
    database_url: str
    db_pool_min_size: int
    db_pool_max_size: int
    db_connect_timeout: int
    db_pool_timeout: float
    db_init_retries: int
    db_init_retry_delay: float


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped if stripped else default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return int(value.strip())


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return float(value.strip())


def load_settings() -> Settings:
    """Carrega o arquivo .env (se existir) e retorna as configurações resolvidas."""
    load_dotenv()
    return Settings(
        app_host=_env_str("APP_HOST", "0.0.0.0"),
        app_port=_env_int("APP_PORT", 8000),
        log_level=_env_str("LOG_LEVEL", "INFO").upper(),
        database_url=_env_str("DATABASE_URL", ""),
        db_pool_min_size=_env_int("DB_POOL_MIN_SIZE", 1),
        db_pool_max_size=_env_int("DB_POOL_MAX_SIZE", 5),
        db_connect_timeout=_env_int("DB_CONNECT_TIMEOUT", 2),
        db_pool_timeout=_env_float("DB_POOL_TIMEOUT", 3.0),
        db_init_retries=_env_int("DB_INIT_RETRIES", 10),
        db_init_retry_delay=_env_float("DB_INIT_RETRY_DELAY", 1.0),
    )
