"""Camada de persistência com suporte em memória (Semana 1) e PostgreSQL (Semana 2)."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
import threading
from typing import Any, Protocol

from src.config import Settings
from src.metrics import DB_POOL_CONEXOES_EM_USO

CATALOGO_INICIAL: list[dict[str, Any]] = [
    {
        "id": 1,
        "nome": "Café Planalto Bourbon Amarelo 250g",
        "descricao": "Notas de caramelo, chocolate ao leite e acidez cítrica equilibrada.",
        "origem": "Planalto da Conquista - BA (1.050m)",
        "torra": "média",
        "preco_reais": 48.90,
        "estoque": 80,
    },
    {
        "id": 2,
        "nome": "Café Planalto Catuaí Vermelho 250g",
        "descricao": "Corpo aveludado com doçura natural de rapadura e amêndoas.",
        "origem": "Barra do Choça - BA (980m)",
        "torra": "média",
        "preco_reais": 42.50,
        "estoque": 120,
    },
    {
        "id": 3,
        "nome": "Café Planalto Mundo Novo 500g",
        "descricao": "Blend clássico para espresso e coado diário, finalização prolongada.",
        "origem": "Vitória da Conquista - BA (950m)",
        "torra": "média-escura",
        "preco_reais": 74.00,
        "estoque": 65,
    },
    {
        "id": 4,
        "nome": "Café Planalto Reserva da Serra Geisha 250g",
        "descricao": "Microlote premiado com notas florais de jasmim e pêssego.",
        "origem": "Chapada Diamantina - BA (1.280m)",
        "torra": "clara",
        "preco_reais": 89.90,
        "estoque": 30,
    },
    {
        "id": 5,
        "nome": "Kit Degustação Planalto (3x 250g)",
        "descricao": "Seleção com Bourbon Amarelo, Catuaí Vermelho e Reserva da Serra.",
        "origem": "Vitória da Conquista - BA",
        "torra": "variada",
        "preco_reais": 129.00,
        "estoque": 40,
    },
]


class DatabaseUnavailableError(Exception):
    """Erro levantado quando o backend de dados não responde."""


class BaseRepository(Protocol):
    """Contrato comum entre repositório em memória e PostgreSQL."""

    def initialize(self) -> None: ...

    def close(self) -> None: ...

    def list_produtos(self) -> list[dict[str, Any]]: ...

    def create_pedido(
        self,
        produto_id: int,
        quantidade: int,
        cliente: str,
    ) -> dict[str, Any] | None: ...

    def list_pedidos(self) -> list[dict[str, Any]]: ...

    def check_health(self) -> tuple[bool, str]: ...


class InMemoryRepository:
    """Armazenamento em memória para desenvolvimento e testes da Semana 1."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._produtos: list[dict[str, Any]] = [dict(item) for item in CATALOGO_INICIAL]
        self._pedidos: list[dict[str, Any]] = []
        self._next_pedido_id = 1

    def initialize(self) -> None:
        DB_POOL_CONEXOES_EM_USO.set(0)

    def close(self) -> None:
        DB_POOL_CONEXOES_EM_USO.set(0)

    def list_produtos(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._produtos]

    def create_pedido(
        self,
        produto_id: int,
        quantidade: int,
        cliente: str,
    ) -> dict[str, Any] | None:
        with self._lock:
            produto = next((p for p in self._produtos if p["id"] == produto_id), None)
            if produto is None:
                return None

            valor_total = round(float(produto["preco_reais"]) * quantidade, 2)
            pedido = {
                "id": self._next_pedido_id,
                "produto_id": produto_id,
                "produto_nome": produto["nome"],
                "quantidade": quantidade,
                "valor_total_reais": valor_total,
                "cliente": cliente,
                "status": "confirmado",
                "criado_em": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
            self._next_pedido_id += 1
            self._pedidos.append(pedido)
            return dict(pedido)

    def list_pedidos(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._pedidos]

    def check_health(self) -> tuple[bool, str]:
        return True, "memory"


class PostgresRepository:
    """Repositório PostgreSQL com pool de conexões e métrica de conexões em uso."""

    def __init__(self, database_url: str, min_size: int = 1, max_size: int = 5) -> None:
        self._database_url = database_url
        self._min_size = min_size
        self._max_size = max_size
        self._pool: Any = None

    def initialize(self) -> None:
        from psycopg_pool import ConnectionPool

        DB_POOL_CONEXOES_EM_USO.set(0)
        self._pool = ConnectionPool(
            conninfo=self._database_url,
            min_size=self._min_size,
            max_size=self._max_size,
            open=True,
        )
        self._ensure_schema_and_seed()

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool = None
        DB_POOL_CONEXOES_EM_USO.set(0)

    @contextmanager
    def _get_connection(self) -> Iterator[Any]:
        if self._pool is None:
            raise DatabaseUnavailableError("Pool de conexões PostgreSQL não inicializado")
        try:
            with self._pool.connection() as conn:
                DB_POOL_CONEXOES_EM_USO.inc()
                try:
                    yield conn
                finally:
                    DB_POOL_CONEXOES_EM_USO.dec()
        except DatabaseUnavailableError:
            raise
        except Exception as exc:
            raise DatabaseUnavailableError(str(exc)) from exc

    def _ensure_schema_and_seed(self) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS produtos (
                        id INTEGER PRIMARY KEY,
                        nome TEXT NOT NULL,
                        descricao TEXT NOT NULL,
                        origem TEXT NOT NULL,
                        torra TEXT NOT NULL,
                        preco_reais NUMERIC(10, 2) NOT NULL,
                        estoque INTEGER NOT NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS pedidos (
                        id SERIAL PRIMARY KEY,
                        produto_id INTEGER NOT NULL REFERENCES produtos(id),
                        produto_nome TEXT NOT NULL,
                        quantidade INTEGER NOT NULL,
                        valor_total_reais NUMERIC(10, 2) NOT NULL,
                        cliente TEXT NOT NULL,
                        status TEXT NOT NULL,
                        criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute("SELECT COUNT(*) FROM produtos")
                count = cur.fetchone()[0]
                if count == 0:
                    for item in CATALOGO_INICIAL:
                        cur.execute(
                            """
                            INSERT INTO produtos (id, nome, descricao, origem, torra, preco_reais, estoque)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                item["id"],
                                item["nome"],
                                item["descricao"],
                                item["origem"],
                                item["torra"],
                                item["preco_reais"],
                                item["estoque"],
                            ),
                        )
            conn.commit()

    def list_produtos(self) -> list[dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, nome, descricao, origem, torra, preco_reais, estoque
                        FROM produtos
                        ORDER BY id
                        """
                    )
                    rows = cur.fetchall()
                    return [
                        {
                            "id": row[0],
                            "nome": row[1],
                            "descricao": row[2],
                            "origem": row[3],
                            "torra": row[4],
                            "preco_reais": float(row[5]),
                            "estoque": row[6],
                        }
                        for row in rows
                    ]
        except DatabaseUnavailableError:
            raise
        except Exception as exc:
            raise DatabaseUnavailableError(str(exc)) from exc

    def create_pedido(
        self,
        produto_id: int,
        quantidade: int,
        cliente: str,
    ) -> dict[str, Any] | None:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT nome, preco_reais FROM produtos WHERE id = %s",
                        (produto_id,),
                    )
                    produto = cur.fetchone()
                    if produto is None:
                        return None

                    produto_nome = produto[0]
                    valor_total = round(float(produto[1]) * quantidade, 2)
                    cur.execute(
                        """
                        INSERT INTO pedidos (produto_id, produto_nome, quantidade, valor_total_reais, cliente, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id, criado_em
                        """,
                        (produto_id, produto_nome, quantidade, valor_total, cliente, "confirmado"),
                    )
                    created = cur.fetchone()
                conn.commit()
                criado_em = created[1].astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                return {
                    "id": created[0],
                    "produto_id": produto_id,
                    "produto_nome": produto_nome,
                    "quantidade": quantidade,
                    "valor_total_reais": valor_total,
                    "cliente": cliente,
                    "status": "confirmado",
                    "criado_em": criado_em,
                }
        except DatabaseUnavailableError:
            raise
        except Exception as exc:
            raise DatabaseUnavailableError(str(exc)) from exc

    def list_pedidos(self) -> list[dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, produto_id, produto_nome, quantidade, valor_total_reais, cliente, status, criado_em
                        FROM pedidos
                        ORDER BY id
                        """
                    )
                    rows = cur.fetchall()
                    return [
                        {
                            "id": row[0],
                            "produto_id": row[1],
                            "produto_nome": row[2],
                            "quantidade": row[3],
                            "valor_total_reais": float(row[4]),
                            "cliente": row[5],
                            "status": row[6],
                            "criado_em": row[7].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                        }
                        for row in rows
                    ]
        except DatabaseUnavailableError:
            raise
        except Exception as exc:
            raise DatabaseUnavailableError(str(exc)) from exc

    def check_health(self) -> tuple[bool, str]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return True, "postgres"
        except Exception:
            return False, "unavailable"


def create_repository(settings: Settings) -> BaseRepository:
    """Seleciona o repositório adequado de acordo com a presença de DATABASE_URL."""
    if settings.database_url:
        return PostgresRepository(
            database_url=settings.database_url,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
        )
    return InMemoryRepository()
