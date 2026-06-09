"""
Utilitários para cálculos de composição nutricional.
"""
import numpy as np
from .constants import NUTRIENTES


def calcular_nutrientes_totais(ingredientes_proporcoes, ingredientes_dados):
    """
    Calcula os nutrientes totais da ração dada as proporções e dados dos ingredientes.

    Args:
        ingredientes_proporcoes: dict {ingrediente_id: proporcao_percentual}
        ingredientes_dados: dict {ingrediente_id: {pb: X, ndt: Y, ...}}

    Returns:
        dict com nutrientes totais
    """
    nutrientes_totais = {nutriente: 0.0 for nutriente in NUTRIENTES.keys()}

    total_proporcao = sum(ingredientes_proporcoes.values())

    if total_proporcao == 0:
        return nutrientes_totais

    for ingrediente_id, proporcao in ingredientes_proporcoes.items():
        if ingrediente_id not in ingredientes_dados:
            continue

        dados = ingredientes_dados[ingrediente_id]
        peso_normalizado = proporcao / total_proporcao

        for nutriente in NUTRIENTES.keys():
            if nutriente in dados:
                nutrientes_totais[nutriente] += dados[nutriente] * peso_normalizado

    return nutrientes_totais


def calcular_custo_total(ingredientes_proporcoes, ingredientes_custos):
    """
    Calcula o custo total da ração.

    Args:
        ingredientes_proporcoes: dict {ingrediente_id: proporcao_percentual}
        ingredientes_custos: dict {ingrediente_id: custo_kg}

    Returns:
        float com custo total (R$/kg)
    """
    custo_total = 0.0
    total_proporcao = sum(ingredientes_proporcoes.values())

    if total_proporcao == 0:
        return custo_total

    for ingrediente_id, proporcao in ingredientes_proporcoes.items():
        if ingrediente_id not in ingredientes_custos:
            continue

        peso_normalizado = proporcao / total_proporcao
        custo_total += ingredientes_custos[ingrediente_id] * peso_normalizado

    return round(custo_total, 4)


def validar_soma_proporcoes(ingredientes_proporcoes, tolerancia=0.1):
    """
    Valida que a soma das proporções é 100% (dentro de tolerância).

    Args:
        ingredientes_proporcoes: dict {ingrediente_id: proporcao_percentual}
        tolerancia: margem de erro aceita

    Returns:
        tuple (is_valid, soma_atual)
    """
    soma = sum(ingredientes_proporcoes.values())
    # Considerando soma em %, não necessário dividir por 100
    diferenca = abs(soma - 100.0)
    is_valid = diferenca <= tolerancia
    return is_valid, soma


def normalizar_proporcoes(ingredientes_proporcoes):
    """
    Normaliza as proporções para somar exatamente 100%.

    Args:
        ingredientes_proporcoes: dict {ingrediente_id: proporcao_percentual}

    Returns:
        dict normalizado
    """
    soma = sum(ingredientes_proporcoes.values())

    if soma == 0:
        return ingredientes_proporcoes

    fator = 100.0 / soma
    return {k: v * fator for k, v in ingredientes_proporcoes.items()}


def calcular_margem_nutriente(valor_obtido, valor_exigido, operador):
    """
    Calcula a margem entre o valor obtido e exigido.

    Args:
        valor_obtido: float
        valor_exigido: float
        operador: str ('=', '>=', '<=')

    Returns:
        float (margem = valor_obtido - valor_exigido)
    """
    return round(valor_obtido - valor_exigido, 4)


def validar_atendimento_restricao(valor_obtido, valor_exigido, operador, tolerancia=0.01):
    """
    Valida se a restrição foi atendida.

    Args:
        valor_obtido: float
        valor_exigido: float
        operador: str ('=', '>=', '<=')
        tolerancia: margem de tolerância

    Returns:
        bool
    """
    if operador == '>=':
        return valor_obtido >= (valor_exigido - tolerancia)
    elif operador == '<=':
        return valor_obtido <= (valor_exigido + tolerancia)
    elif operador == '=':
        return abs(valor_obtido - valor_exigido) <= tolerancia

    return False


def formatar_nutriente_para_display(valor, nutriente):
    """
    Formata um valor de nutriente para exibição.

    Args:
        valor: float
        nutriente: str (chave em NUTRIENTES)

    Returns:
        str formatado
    """
    if nutriente not in NUTRIENTES:
        return str(round(valor, 2))

    unidade = NUTRIENTES[nutriente]['unidade']
    return f"{round(valor, 2)} {unidade}"
