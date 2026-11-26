"""Modelos Pydantic de entrada e saída da API Café Planalto."""

from pydantic import BaseModel, Field


class Produto(BaseModel):
    """Item do catálogo de cafés especiais."""

    id: int
    nome: str
    descricao: str
    origem: str
    torra: str
    preco_reais: float
    estoque: int


class PedidoCreate(BaseModel):
    """Payload para criação de um novo pedido."""

    produto_id: int = Field(..., ge=1, description="ID do café selecionado")
    quantidade: int = Field(default=1, ge=1, le=100, description="Quantidade de unidades")
    cliente: str = Field(
        default="cliente-loja",
        min_length=1,
        max_length=120,
        description="Identificação do cliente (registrada apenas em logs, nunca como label)",
    )


class PedidoResponse(BaseModel):
    """Representação de um pedido registrado pela loja."""

    id: int
    produto_id: int
    produto_nome: str
    quantidade: int
    valor_total_reais: float
    cliente: str
    status: str
    criado_em: str


class CaosConfig(BaseModel):
    """Parâmetros aceitos por POST /admin/caos para ligar ou desligar falhas."""

    latencia_ms: int | None = Field(
        default=None,
        ge=0,
        le=30000,
        description="Atraso artificial em milissegundos adicionado às rotas da loja",
    )
    taxa_erro: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Fração de requisições que falham com HTTP 500 (0.0 a 1.0)",
    )


class CaosStatus(BaseModel):
    """Estado atual da injeção de caos."""

    latencia_ms: int
    taxa_erro: float
    ativo: bool


class HealthResponse(BaseModel):
    """Resposta do endpoint /health indicando estado da API e do banco."""

    status: str
    database: str
