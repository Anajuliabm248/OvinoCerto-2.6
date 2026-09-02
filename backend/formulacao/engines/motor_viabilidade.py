"""
MotorViabilidade — Quadros 9 a 14 da planilha "Custos e Viabilidade da Dieta".

Motor puro, sem I/O — mesmo contrato de MotorCusto/MotorRecalculo.

Mapeamento Quadro -> aqui
  Quadro 4  (Dados do(s) animal(s))   -> fora deste motor: leitura direta
                                          de Lote/ExigenciaConfigurada,
                                          sem cálculo (espécie, raça,
                                          categoria, peso NRC).
  Quadro 5 (Índices Zootécnicos)     -> ParametrosViabilidade (input) +
                                          IndicesZootecnicos (calculado).
  Quadro 6 (Custos Finais da Dieta)  -> LinhaCustoIngrediente[] + totais.
  Quadro 7 (Preço mínimo p/ lucro)   -> SaidaViabilidade.preco_minimo_kg_pv.
  Quadro 8 (Valor R$/kg PV)          -> ParametrosViabilidade.preco_venda_kg_pv
                                          (é um INPUT do usuário, não algo
                                          calculado por este motor).
  Quadro 9 (Resultado Econômico)     -> resultado_animal / resultado_lote.

IMPORTANTE — separação de responsabilidade (requisito explícito):
os parâmetros de ParametrosViabilidade (num_animais, gmd_esperado_kg,
peso_entrada_kg, estimativa_permanencia_dias, cms_percentual_pv,
perdas_alimentos_percentual) são uma CÓPIA editável, independente do
Lote e da ExigenciaConfigurada — mesmo padrão já usado para
ExigenciaConfigurada em relação a EXIGENCIA_NRC (arquitetura, seção 15:
"nunca altera o padrão"). Editar esses valores para simular cenários
de custo NUNCA realimenta nem altera a formulação nutricional, o Lote
ou a ExigenciaConfigurada.

ATENÇÃO À NOMENCLATURA: `cms_percentual_pv` aqui é DIFERENTE de
ExigenciaConfigurada.cms_kg (usado por MotorRecalculo/MotorCusto). Na
planilha, CMS é um percentual do peso vivo (kg de MS consumido por kg
de peso vivo, ex. 2.97 %) usado só para projetar consumo ao longo do
período de confinamento — não é a exigência nutricional oficial. Os
dois NUNCA devem ser confundidos nem sincronizados automaticamente.

`participacao_mn_percentual` (coluna D do Quadro 6) é a participação
de cada ingrediente em base de matéria natural (MN), ANTES de aplicar
perdas — não confundir com a participação em %MS (`fracoes_ms`, que
vem de ParticipacaoVetor e é a base de toda a adequação nutricional).
São duas visões do mesmo ingrediente, em bases diferentes; ambas
corretas, cada uma no seu contexto.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ParametrosViabilidade:
    """Quadro 5 (+ Quadro 8) — entrada editável, independente do Lote/Exigência."""
    num_animais: int
    gmd_esperado_kg: float
    estimativa_permanencia_dias: int
    peso_entrada_kg: float
    cms_percentual_pv: float             # fração 0-1, ex. 0.0297 = 2.97 % do PV
    perdas_alimentos_percentual: float   # fração 0-1, ex. 0.08 = 8 %
    preco_venda_kg_pv: float | None      # Quadro 8, R$/kg de peso vivo


@dataclass(frozen=True)
class IndicesZootecnicos:
    """Resultado calculado do Quadro 5 (equivalentes a E15-E18 da planilha)."""
    peso_saida_kg: float
    ganho_peso_kg: float
    peso_ajustado_kg: float
    cms_kg_dia: float


@dataclass(frozen=True)
class LinhaCustoIngrediente:
    """Uma linha do Quadro 6."""
    ingrediente_id: int | None
    nome: str
    participacao_mn_percentual: float   # D: % (MN), share do ingrediente em MN, pré-perdas
    consumo_kg_dia_animal: float        # E: Kg/dia (MN) por animal, já com perdas aplicadas
    consumo_kg_dia_lote: float          # F: Kg/dia do lote
    kg_total_periodo: float             # G: Kg Ingred. (total a adquirir no período)
    preco_kg_mn: float                  # H: R$/Kg
    investimento_total: float           # I: R$/total
    percentual_investimento: float      # J: %/Animal (participação no investimento total)
    custo_por_animal: float             # K: R$/Anim. (total no período)
    custo_por_animal_dia: float         # L: R$/dia


@dataclass(frozen=True)
class ResultadoEconomicoLinha:
    """Uma linha (Animal ou Lote) do Quadro 9."""
    renda_bruta_total: float
    custo_total: float
    custo_por_dia: float
    viabilidade_total: float     # lucro (positivo) ou prejuízo (negativo)
    viabilidade_por_dia: float


@dataclass(frozen=True)
class SaidaViabilidade:
    """Consolida consumo, investimento, preço mínimo e resultado do cenário."""
    indices: IndicesZootecnicos
    linhas_custo: list[LinhaCustoIngrediente]
    consumo_total_percentual: float
    consumo_kg_dia_animal_total: float
    consumo_kg_dia_lote_total: float
    kg_total_periodo_total: float
    investimento_total_geral: float
    custo_por_animal_total: float
    custo_por_animal_dia_total: float
    preco_minimo_kg_pv: float | None
    resultado_animal: ResultadoEconomicoLinha | None
    resultado_lote: ResultadoEconomicoLinha | None


class MotorViabilidade:
    """Motor puro — replica os Quadros 9-14 da planilha "Custos e Viabilidade"."""

    @staticmethod
    def calcular(
        parametros: ParametrosViabilidade,
        fracoes_ms: np.ndarray,       # participação 0-1 por ingrediente (%MS), mesma ordem sempre
        ms_percentuais: np.ndarray,   # MS (%) por ingrediente
        precos_kg_mn: np.ndarray,     # R$/kg MN por ingrediente; 0.0 = sem preço
        nomes: list[str],
        ingrediente_ids: list[int | None],
    ) -> SaidaViabilidade:
        """Projeta o cenário econômico usando vetores alinhados por ingrediente."""
        p = parametros
        fracoes_ms     = np.asarray(fracoes_ms, dtype=float)
        ms_percentuais = np.asarray(ms_percentuais, dtype=float)
        precos_kg_mn   = np.asarray(precos_kg_mn, dtype=float)
        MotorViabilidade._validar_entrada(
            p,
            fracoes_ms,
            ms_percentuais,
            precos_kg_mn,
            nomes,
            ingrediente_ids,
        )
        indices = MotorViabilidade._calcular_indices(p)

        # E: ms do ingrediente (kg/dia/animal) -> mn bruto (kg/dia/animal, sem perdas)
        ms_kg_dia_animal = fracoes_ms * indices.cms_kg_dia
        mn_kg_dia_bruto = np.divide(
            ms_kg_dia_animal, ms_percentuais / 100.0,
            out=np.zeros_like(ms_kg_dia_animal), where=ms_percentuais > 0,
        )
        # E: aplica perdas (sobras) -> consumo real a fornecer
        mn_kg_dia_animal = mn_kg_dia_bruto * (1.0 + p.perdas_alimentos_percentual)

        # F, G, I: lote, período, investimento
        consumo_kg_dia_lote = (mn_kg_dia_animal * p.num_animais)
        kg_total_periodo    = consumo_kg_dia_lote * p.estimativa_permanencia_dias
        investimento_total  = kg_total_periodo * precos_kg_mn

        investimento_total_geral = float(investimento_total.sum())
        mn_bruto_total            = float(mn_kg_dia_bruto.sum())

        # J: % do investimento total que cada ingrediente representa
        percentual_investimento = np.divide(
            investimento_total * 100.0, investimento_total_geral,
            out=np.zeros_like(investimento_total), where=investimento_total_geral > 0,
        )
        # D: participação de cada ingrediente em base MN (pré-perdas)
        participacao_mn_percentual = np.divide(
            mn_kg_dia_bruto * 100.0, mn_bruto_total,
            out=np.zeros_like(mn_kg_dia_bruto), where=mn_bruto_total > 0,
        )

        # K, L: custo por animal (total no período) e por dia
        custo_por_animal = (
            investimento_total / p.num_animais
            if p.num_animais > 0 else np.zeros_like(investimento_total)
        )
        custo_por_animal_dia = (
            custo_por_animal / p.estimativa_permanencia_dias
            if p.estimativa_permanencia_dias > 0 else np.zeros_like(custo_por_animal)
        )

        linhas = [
            LinhaCustoIngrediente(
                ingrediente_id=ingrediente_ids[i],
                nome=nomes[i],
                participacao_mn_percentual=float(participacao_mn_percentual[i]),
                consumo_kg_dia_animal=float(mn_kg_dia_animal[i]),
                consumo_kg_dia_lote=float(consumo_kg_dia_lote[i]),
                kg_total_periodo=float(kg_total_periodo[i]),
                preco_kg_mn=float(precos_kg_mn[i]),
                investimento_total=float(investimento_total[i]),
                percentual_investimento=float(percentual_investimento[i]),
                custo_por_animal=float(custo_por_animal[i]),
                custo_por_animal_dia=float(custo_por_animal_dia[i]),
            )
            for i in range(len(fracoes_ms))
        ]

        custo_por_animal_total     = float(custo_por_animal.sum())
        custo_por_animal_dia_total = float(custo_por_animal_dia.sum())

        preco_minimo_kg_pv = None
        resultado_animal = None
        resultado_lote = None
        if p.preco_venda_kg_pv is not None:
            # Quadros 7 e 9 só fazem sentido quando o cenário econômico
            # inclui o preço de venda do peso vivo (Quadro ).
            preco_minimo_kg_pv = (
                custo_por_animal_total / indices.ganho_peso_kg
                if indices.ganho_peso_kg > 0 else 0.0
            )
            resultado_animal = MotorViabilidade._resultado_economico(
                renda_bruta_total=indices.ganho_peso_kg * p.preco_venda_kg_pv,
                custo_total=custo_por_animal_total,
                dias=p.estimativa_permanencia_dias,
            )
            resultado_lote = MotorViabilidade._resultado_economico(
                renda_bruta_total=(
                    indices.ganho_peso_kg * p.preco_venda_kg_pv * p.num_animais
                ),
                custo_total=investimento_total_geral,
                dias=p.estimativa_permanencia_dias,
            )

        return SaidaViabilidade(
            indices=indices,
            linhas_custo=linhas,
            consumo_total_percentual=float(participacao_mn_percentual.sum()),
            consumo_kg_dia_animal_total=float(mn_kg_dia_animal.sum()),
            consumo_kg_dia_lote_total=float(consumo_kg_dia_lote.sum()),
            kg_total_periodo_total=float(kg_total_periodo.sum()),
            investimento_total_geral=investimento_total_geral,
            custo_por_animal_total=custo_por_animal_total,
            custo_por_animal_dia_total=custo_por_animal_dia_total,
            preco_minimo_kg_pv=preco_minimo_kg_pv,
            resultado_animal=resultado_animal,
            resultado_lote=resultado_lote,
        )

    @staticmethod
    def _validar_entrada(
        p: ParametrosViabilidade,
        fracoes_ms: np.ndarray,
        ms_percentuais: np.ndarray,
        precos_kg_mn: np.ndarray,
        nomes: list[str],
        ingrediente_ids: list[int | None],
    ) -> None:
        """Interrompe cedo quando quantidades ou vetores tornariam o cenário enganoso."""
        vetores = (fracoes_ms, ms_percentuais, precos_kg_mn)
        if any(vetor.ndim != 1 for vetor in vetores):
            raise ValueError('Os vetores da viabilidade devem ser unidimensionais.')
        tamanho = len(fracoes_ms)
        if any(len(vetor) != tamanho for vetor in vetores[1:]) or not (
            len(nomes) == len(ingrediente_ids) == tamanho
        ):
            raise ValueError('Todos os dados de ingredientes devem ter o mesmo tamanho.')
        if np.any(~np.isfinite(fracoes_ms)) or np.any(fracoes_ms < 0):
            raise ValueError('As participações devem ser finitas e não negativas.')
        if np.any(~np.isfinite(ms_percentuais)) or np.any(
            (ms_percentuais <= 0) | (ms_percentuais > 100)
        ):
            raise ValueError('A matéria seca de cada ingrediente deve estar entre 0% e 100%.')
        if np.any(~np.isfinite(precos_kg_mn)) or np.any(precos_kg_mn < 0):
            raise ValueError('Os preços devem ser finitos e não negativos.')
        if p.num_animais <= 0:
            raise ValueError('A quantidade de animais deve ser maior que zero.')
        if p.estimativa_permanencia_dias <= 0:
            raise ValueError('A permanência deve ser maior que zero dia.')
        if p.peso_entrada_kg <= 0:
            raise ValueError('O peso de entrada deve ser maior que zero.')
        if p.gmd_esperado_kg < 0:
            raise ValueError('O ganho médio diário não pode ser negativo.')
        if not 0 < p.cms_percentual_pv <= 1:
            raise ValueError('O percentual de CMS deve ser uma fração entre 0 e 1.')
        if not 0 <= p.perdas_alimentos_percentual <= 1:
            raise ValueError('As perdas devem ser uma fração entre 0 e 1.')
        if p.preco_venda_kg_pv is not None and p.preco_venda_kg_pv < 0:
            raise ValueError('O preço de venda não pode ser negativo.')

    @staticmethod
    def _calcular_indices(p: ParametrosViabilidade) -> IndicesZootecnicos:
        """
        Réplica direta de E15-E18 da planilha:
          peso_saida    = peso_entrada + gmd * dias
          ganho_peso    = peso_saida - peso_entrada  ( == gmd * dias )
          peso_ajustado = média(peso_entrada, peso_saida)
          cms_kg_dia    = peso_ajustado * cms_percentual_pv
        """
        peso_saida    = p.peso_entrada_kg + p.gmd_esperado_kg * p.estimativa_permanencia_dias
        ganho         = peso_saida - p.peso_entrada_kg
        peso_ajustado = (p.peso_entrada_kg + peso_saida) / 2.0
        cms_kg_dia    = peso_ajustado * p.cms_percentual_pv
        return IndicesZootecnicos(
            peso_saida_kg=peso_saida,
            ganho_peso_kg=ganho,
            peso_ajustado_kg=peso_ajustado,
            cms_kg_dia=cms_kg_dia,
        )

    @staticmethod
    def _resultado_economico(
        renda_bruta_total: float,
        custo_total: float,
        dias: int,
    ) -> ResultadoEconomicoLinha:
        """Compara renda e custo no período e também apresenta valores diários."""
        viabilidade_total = renda_bruta_total - custo_total
        return ResultadoEconomicoLinha(
            renda_bruta_total=renda_bruta_total,
            custo_total=custo_total,
            custo_por_dia=custo_total / dias if dias > 0 else 0.0,
            viabilidade_total=viabilidade_total,
            viabilidade_por_dia=viabilidade_total / dias if dias > 0 else 0.0,
        )
