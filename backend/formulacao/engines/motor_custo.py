"""Calcula o custo diário da dieta a partir das participações em matéria seca."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

@dataclass(frozen=True)
class EntradaCusto:
    """Reúne vetores alinhados e os dados de consumo necessários ao cálculo."""
    fracoes_ms: np.ndarray          # participação 0-1, mesma ordem do MotorRecalculo
    custos_kg_mn: np.ndarray        # R$/kg MN por ingrediente (já resolvido: override > catálogo)
    ms_percentuais: np.ndarray      # MS% de cada ingrediente (para converter MN -> MS)
    cms_total_kg: float
    num_animais: int

@dataclass(frozen=True)
class SaidaCusto:
    """Entrega custos unitários, por animal e por lote, além de alertas de preço."""
    custo_por_ingrediente_dia: np.ndarray   # R$/dia que cada ingrediente contribui
    custo_ms_kg: float                       # R$ por kg de MS da formulação
    custo_mn_kg: float                       # R$ por kg de MN da formulação
    custo_animal_dia: float
    custo_lote_dia: float
    tem_ingrediente_sem_preco: bool          # sinaliza para o MotorAlertas

class MotorCusto:
    """Converte matéria seca em matéria natural e aplica o preço de cada item."""

    @staticmethod
    def calcular(entrada: EntradaCusto) -> SaidaCusto:
        """Calcula custos sem alterar a entrada e rejeita valores fisicamente inválidos."""
        fracoes = np.asarray(entrada.fracoes_ms, dtype=float)
        custos = np.asarray(entrada.custos_kg_mn, dtype=float)
        teores_ms = np.asarray(entrada.ms_percentuais, dtype=float)

        if not (fracoes.ndim == custos.ndim == teores_ms.ndim == 1):
            raise ValueError('Os vetores de custo devem ser unidimensionais.')
        if not (len(fracoes) == len(custos) == len(teores_ms)):
            raise ValueError('Participações, preços e teores de MS devem ter o mesmo tamanho.')
        if np.any(~np.isfinite(fracoes)) or np.any(fracoes < 0):
            raise ValueError('As participações devem ser números finitos e não negativos.')
        if np.any(~np.isfinite(custos)) or np.any(custos < 0):
            raise ValueError('Os preços devem ser números finitos e não negativos.')
        if np.any(~np.isfinite(teores_ms)) or np.any((teores_ms <= 0) | (teores_ms > 100)):
            raise ValueError('Todo ingrediente deve ter matéria seca maior que 0% e até 100%.')
        if entrada.cms_total_kg < 0:
            raise ValueError('O consumo de matéria seca não pode ser negativo.')
        if entrada.num_animais <= 0:
            raise ValueError('A quantidade de animais deve ser maior que zero.')

        ms_kg_ing = fracoes * entrada.cms_total_kg
        mn_kg_ing = np.divide(
            ms_kg_ing, teores_ms / 100.0,
            out=np.zeros_like(ms_kg_ing), where=teores_ms > 0,
        )
        custo_ing_dia = mn_kg_ing * custos

        custo_total_dia = float(custo_ing_dia.sum())
        mn_total_kg = float(mn_kg_ing.sum())

        return SaidaCusto(
            custo_por_ingrediente_dia=custo_ing_dia,
            custo_ms_kg=custo_total_dia / entrada.cms_total_kg if entrada.cms_total_kg > 0 else 0.0,
            custo_mn_kg=custo_total_dia / mn_total_kg if mn_total_kg > 0 else 0.0,
            custo_animal_dia=custo_total_dia,
            custo_lote_dia=custo_total_dia * entrada.num_animais,
            tem_ingrediente_sem_preco=bool(np.any((fracoes > 1e-12) & (custos <= 0))),
        )
