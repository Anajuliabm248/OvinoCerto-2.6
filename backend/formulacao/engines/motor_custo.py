from __future__ import annotations

from dataclasses import dataclass

import numpy as np

@dataclass(frozen=True)
class EntradaCusto:
    fracoes_ms: np.ndarray          # participação 0-1, mesma ordem do MotorRecalculo
    custos_kg_mn: np.ndarray        # R$/kg MN por ingrediente (já resolvido: override > catálogo)
    ms_percentuais: np.ndarray      # MS% de cada ingrediente (para converter MN -> MS)
    cms_total_kg: float
    num_animais: int

@dataclass(frozen=True)
class SaidaCusto:
    custo_por_ingrediente_dia: np.ndarray   # R$/dia que cada ingrediente contribui
    custo_ms_kg: float                       # R$ por kg de MS da formulação
    custo_mn_kg: float                       # R$ por kg de MN da formulação
    custo_animal_dia: float
    custo_lote_dia: float
    tem_ingrediente_sem_preco: bool          # sinaliza para o MotorAlertas

class MotorCusto:
    @staticmethod
    def calcular(entrada: EntradaCusto) -> SaidaCusto:
        ms_kg_ing = entrada.fracoes_ms * entrada.cms_total_kg
        mn_kg_ing = np.divide(
            ms_kg_ing, entrada.ms_percentuais / 100.0,
            out=np.zeros_like(ms_kg_ing), where=entrada.ms_percentuais > 0,
        )
        custo_ing_dia = mn_kg_ing * entrada.custos_kg_mn

        custo_total_dia = float(custo_ing_dia.sum())
        mn_total_kg = float(mn_kg_ing.sum())

        return SaidaCusto(
            custo_por_ingrediente_dia=custo_ing_dia,
            custo_ms_kg=custo_total_dia / entrada.cms_total_kg if entrada.cms_total_kg > 0 else 0.0,
            custo_mn_kg=custo_total_dia / mn_total_kg if mn_total_kg > 0 else 0.0,
            custo_animal_dia=custo_total_dia,
            custo_lote_dia=custo_total_dia * entrada.num_animais,
            tem_ingrediente_sem_preco=bool(np.any(entrada.custos_kg_mn <= 0)),
        )
