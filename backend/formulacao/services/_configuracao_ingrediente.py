"""
Helper compartilhado - construção de ConfiguracaoIngrediente.

Usado por GerarFormulacaoInicialService, AdicionarIngredienteService e
RemoverIngredienteService para popular os bounds (limite_min/limite_max)
que o MotorAdequacao usa ao (re)otimizar as participações CALCULADA.

O MotorAdequacao é desacoplado do ORM (formulacao/engines/motor_adequacao.py);
esta função faz a tradução Ingrediente (model) → ConfiguracaoIngrediente
(dataclass de domínio), incluindo classificação, tipo e o limite máximo
convertido de percentual para fração.

Ingredientes sem limite configurado (None) ou ausentes (registro órfão,
ingrediente removido do catálogo) não recebem nenhuma restrição adicional
além da soma total — limite_max cai no default 1.0 (100%).
"""

from __future__ import annotations

from formulacao.engines.motor_adequacao import ConfiguracaoIngrediente
from ingrediente.models import Ingrediente


def configuracao_a_partir_do_ingrediente(
    ingrediente: Ingrediente | None,
    limite_min: float | None = None,
    custo_kg_mn: float | None = None,
) -> ConfiguracaoIngrediente:
    """
    Constrói a ConfiguracaoIngrediente que o MotorAdequacao espera.

    Os limites mínimo e máximo do model estão em percentual (0-100) da MS;
    aqui são convertidos para fração (0-1). ``None`` significa sem limite.

    O limite convertido é sempre mantido dentro de [limite_min, 1.0]
    para nunca violar a validação de ConfiguracaoIngrediente, mesmo em
    cadastros com valores extremos.
    """
    classificacao = (
        (ingrediente.classificacao if ingrediente else "concentrado") or "concentrado"
    ).upper()
    tipo = ((ingrediente.tipo if ingrediente else "outro") or "outro").upper()

    if limite_min is None:
        limite_min = 0.0
        if ingrediente is not None and ingrediente.limite_min_participacao is not None:
            limite_min = ingrediente.limite_min_participacao / 100.0
    limite_min = max(0.0, min(1.0, limite_min))

    limite_max = 1.0
    if ingrediente is not None and ingrediente.limite_max_participacao is not None:
        limite_max = ingrediente.limite_max_participacao / 100.0
        limite_max = max(limite_min, min(1.0, limite_max))

    custo_por_kg_ms = None
    if custo_kg_mn is not None and ingrediente is not None and ingrediente.ms > 0.0:
        custo_por_kg_ms = custo_kg_mn / (ingrediente.ms / 100.0)

    return ConfiguracaoIngrediente(
        classificacao=classificacao,
        tipo=tipo,
        limite_min=limite_min,
        limite_max=limite_max,
        custo_por_kg_ms=custo_por_kg_ms,
    )
