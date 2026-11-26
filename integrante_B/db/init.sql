CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    descricao TEXT NOT NULL,
    origem TEXT NOT NULL,
    torra TEXT NOT NULL,
    preco_reais NUMERIC(10, 2) NOT NULL,
    estoque INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS pedidos (
    id SERIAL PRIMARY KEY,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    produto_nome TEXT NOT NULL,
    quantidade INTEGER NOT NULL,
    valor_total_reais NUMERIC(10, 2) NOT NULL,
    cliente TEXT NOT NULL,
    status TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO produtos (id, nome, descricao, origem, torra, preco_reais, estoque)
VALUES
    (1, 'Café Planalto Bourbon Amarelo 250g', 'Notas de caramelo, chocolate ao leite e acidez cítrica equilibrada.', 'Planalto da Conquista - BA (1.050m)', 'média', 48.90, 80),
    (2, 'Café Planalto Catuaí Vermelho 250g', 'Corpo aveludado com doçura natural de rapadura e amêndoas.', 'Barra do Choça - BA (980m)', 'média', 42.50, 120),
    (3, 'Café Planalto Mundo Novo 500g', 'Blend clássico para espresso e coado diário, finalização prolongada.', 'Vitória da Conquista - BA (950m)', 'média-escura', 74.00, 65),
    (4, 'Café Planalto Reserva da Serra Geisha 250g', 'Microlote premiado com notas florais de jasmim e pêssego.', 'Chapada Diamantina - BA (1.280m)', 'clara', 89.90, 30),
    (5, 'Kit Degustação Planalto (3x 250g)', 'Seleção com Bourbon Amarelo, Catuaí Vermelho e Reserva da Serra.', 'Vitória da Conquista - BA', 'variada', 129.00, 40)
ON CONFLICT (id) DO NOTHING;
