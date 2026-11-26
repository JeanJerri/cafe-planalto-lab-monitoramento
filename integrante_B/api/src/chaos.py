"""Gerenciamento de estado para injeção controlada de caos (latência e falhas HTTP)."""

import random
import threading

# Endpoints administrativos e de observabilidade permanecem imunes ao caos para
# permitir desligar falhas, manter o /metrics coletável pelo Prometheus e deixar
# o /health refletir exclusivamente a saúde do banco de dados.
CHAOS_EXEMPT_PATHS = frozenset(
    {
        "/health",
        "/metrics",
        "/admin/caos",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)


class ChaosState:
    """Mantém de forma thread-safe os parâmetros ativos de injeção de caos."""

    def __init__(self, latencia_ms: int = 0, taxa_erro: float = 0.0) -> None:
        self._lock = threading.Lock()
        self._latencia_ms = latencia_ms
        self._taxa_erro = taxa_erro

    @property
    def latencia_ms(self) -> int:
        with self._lock:
            return self._latencia_ms

    @property
    def taxa_erro(self) -> float:
        with self._lock:
            return self._taxa_erro

    def update(
        self,
        latencia_ms: int | None = None,
        taxa_erro: float | None = None,
    ) -> dict[str, int | float | bool]:
        """Atualiza os parâmetros informados e retorna o estado consolidado."""
        with self._lock:
            if latencia_ms is not None:
                self._latencia_ms = latencia_ms
            if taxa_erro is not None:
                self._taxa_erro = float(taxa_erro)
            return self._snapshot_unlocked()

    def reset(self) -> dict[str, int | float | bool]:
        """Desliga todas as falhas injetadas."""
        return self.update(latencia_ms=0, taxa_erro=0.0)

    def snapshot(self) -> dict[str, int | float | bool]:
        """Retorna cópia imutável do estado atual do caos."""
        with self._lock:
            return self._snapshot_unlocked()

    def should_fail(self) -> bool:
        """Decide probabilisticamente se a requisição atual deve falhar com HTTP 500."""
        with self._lock:
            taxa = self._taxa_erro
        if taxa <= 0.0:
            return False
        if taxa >= 1.0:
            return True
        return random.random() < taxa

    def _snapshot_unlocked(self) -> dict[str, int | float | bool]:
        return {
            "latencia_ms": self._latencia_ms,
            "taxa_erro": self._taxa_erro,
            "ativo": self._latencia_ms > 0 or self._taxa_erro > 0.0,
        }
