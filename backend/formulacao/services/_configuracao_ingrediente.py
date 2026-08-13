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
    limite_min: float = 0.0,
) -> ConfiguracaoIngrediente:
    """
    Constrói a ConfiguracaoIngrediente que o MotorAdequacao espera.

    limite_max_participacao no model está em percentual (0-100) da MS;
    aqui é convertido para fração (0-1). None = sem limite (1.0, ou
    seja, limitado apenas pela soma total = 100%).

    O limite convertido é sempre mantido dentro de [limite_min, 1.0]
    para nunca violar a validação de ConfiguracaoIngrediente, mesmo em
    cadastros com valores extremos.
    """
    classificacao = (
        (ingrediente.classificacao if ingrediente else "concentrado") or "concentrado"
    ).upper()
    tipo = ((ingrediente.tipo if ingrediente else "outro") or "outro").upper()

    limite_max = 1.0
    if ingrediente is not None and ingrediente.limite_max_participacao is not None:
        limite_max = ingrediente.limite_max_participacao / 100.0
        limite_max = max(limite_min, min(1.0, limite_max))

    return ConfiguracaoIngrediente(
        classificacao=classificacao,
        tipo=tipo,
        limite_min=limite_min,
        limite_max=limite_max,
    )
