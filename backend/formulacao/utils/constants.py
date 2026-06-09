"""
Constantes e configurações para o módulo de formulação.
"""

NUTRIENTES = {
    'PB': {'nome': 'Proteína Bruta', 'unidade': '%', 'min': 0.1, 'max': 100},
    'NDT': {'nome': 'Nutrientes Digestíveis Totais', 'unidade': '%', 'min': 0.1, 'max': 100},
    'FDN': {'nome': 'Fibra Detergente Neutro', 'unidade': '%', 'min': 0.1, 'max': 100},
    'EE': {'nome': 'Extrato Etéreo', 'unidade': '%', 'min': 0.1, 'max': 50},
    'Ca': {'nome': 'Cálcio', 'unidade': '%', 'min': 0.01, 'max': 10},
    'P': {'nome': 'Fósforo', 'unidade': '%', 'min': 0.01, 'max': 10},
}

OBJETIVO_TIPOS = {
    'CUSTO': 'Minimizar custo',
    'PB': 'Maximizar proteína bruta',
    'NDT': 'Maximizar NDT',
    'FDN': 'Minimizar FDN',
    'EE': 'Minimizar extrato etéreo',
}

OPERADORES_VALIDOS = ['=', '>=', '<=']

# Tolerâncias para validação
TOLERANCIA_SOMA = 0.1  # Soma de proporções deve ser 100 ± 0.1
TOLERANCIA_IGUALDADE_NUTRIENTE = 0.05  # Nutrientes com = devem estar ±0.05
TOLERANCIA_PERCENTUAL = 0.01  # 1% de tolerância para nutrientes em %

# Limites de proporção por ingrediente
PROPORCAO_MIN_INGREDIENTE = 0.0  # 0%
PROPORCAO_MAX_INGREDIENTE = 100.0  # 100%

# Escala de normalização para objetivos (evita um "engulir" os outros)
ESCALA_CUSTO_MIN = 1.0  # R$/kg
ESCALA_CUSTO_MAX = 10.0  # R$/kg

# Relação Ca:P típica (2:1)
RELACAO_CA_P_ALVO = 2.0
TOLERANCIA_CA_P = 0.3  # ±0.3 de tolerância
