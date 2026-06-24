"""
dado um conjunto de participações (%MS) e a matriz
nutricional dos ingredientes, calcula o vetor nutricional total da
formulação, compara contra os RequisitoNutriente configurados e
produz um ResultadoAdequacao.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .nutrientes import N_NUTRIENTES, Nutriente
from .participacao import ParticipacaoVetor
from .requisito import RequisitoNutriente
from .resultado import ResultadoAdequacao
from .vetor_nutricional import VetorNutricional

# Fator de conversão de "% da MS" para fração (0-1), usado apenas
# na etapa de cálculo de massa absoluta (kg/dia) por nutriente.
PERCENTUAL_PARA_FRACAO = 1.0 / 100.0


@dataclass(frozen=True)
class ResultadoPorIngrediente:
    """
    Resultado individual de um ingrediente dentro da formulação,
    em massa absoluta (kg/dia) - usado pelo repositório para
    persistir os campos `*_kg` de IngredienteFormulacao.
    """

    id_ingrediente: int
    fracao_ms: float          # 0-1
    ms_kg: float               # kg de MS/dia deste ingrediente
    nutrientes_kg: VetorNutricional  # kg/dia de cada nutriente

    def to_dict(self) -> dict:
        return {
            "id_ingrediente": self.id_ingrediente,
            "fracao_ms": self.fracao_ms,
            "ms_kg": self.ms_kg,
            "nutrientes_kg": self.nutrientes_kg.to_dict(),
        }


@dataclass(frozen=True)
class ResultadoRecalculo:
    """
    Saída completa do MotorRecalculo
    o que o repositório precisa para persistir IngredienteFormulacao
    e criar o SnapshotFormulacao.
    """

    resultado_adequacao: ResultadoAdequacao
    vetor_total_pct: VetorNutricional  # % da MS da formulação inteira
    por_ingrediente: tuple[ResultadoPorIngrediente, ...]
    cms_total_kg: float

    def to_dict(self) -> dict:
        return {
            "cms_total_kg": self.cms_total_kg,
            "vetor_total_pct": self.vetor_total_pct.to_dict(),
            "resultado_adequacao": self.resultado_adequacao.to_dict(),
            "por_ingrediente": [i.to_dict() for i in self.por_ingrediente],
        }


class MotorRecalculo:
    """
    Serviço de domínio puro. Não possui estado - todos os métodos
    são estáticos/puros, recebem tudo que precisam por parâmetro.
    """

    @staticmethod
    def calcular(
        participacao: ParticipacaoVetor,
        matriz_nutricional: dict[int, VetorNutricional],
        requisitos: dict[Nutriente, RequisitoNutriente],
        cms_total_kg: float,
    ) -> ResultadoRecalculo:
        """
        participacao       : ParticipacaoVetor com as fracoes (0-1)
                              de cada ingrediente.
        matriz_nutricional : dict {id_ingrediente: VetorNutricional},
                              valores em % da MS (ex.: PB=18.5).
        requisitos          : dict {Nutriente: RequisitoNutriente},
                              vindo da ExigenciaConfigurada.
        cms_total_kg        : Consumo de Matéria Seca total do lote
                              (kg/dia), usado apenas para converter
                              fracoes em massa absoluta.

        Levanta KeyError se algum id de `participacao.ids_ingredientes`
        não existir em `matriz_nutricional` - falha rápida e explícita
        em vez de silenciar dados ausentes.
        """
        if len(participacao) == 0:
            # Formulação vazia: vetor total é zero e soma é zero.
            # A invalidade (`soma=0`) é sinalizada via soma_valida=False
            # dentro de ResultadoAdequacao; bloquear isso é regra de
            # negócio do Application Service (seção 16), não do motor.
            vetor_total = VetorNutricional.zeros()
            resultado_adequacao = ResultadoAdequacao.calcular(
                vetor_total=vetor_total,
                requisitos=requisitos,
                soma_participacoes=0.0,
            )
            return ResultadoRecalculo(
                resultado_adequacao=resultado_adequacao,
                vetor_total_pct=vetor_total,
                por_ingrediente=(),
                cms_total_kg=cms_total_kg,
            )

        # 1. Monta a matriz M (n_ingredientes x N_NUTRIENTES), na
        #    mesma ordem de participacao.ids_ingredientes.
        try:
            linhas = [
                matriz_nutricional[id_ingrediente].valores
                for id_ingrediente in participacao.ids_ingredientes
            ]
        except KeyError as exc:
            raise KeyError(
                f"Ingrediente id={exc.args[0]} presente em ParticipacaoVetor "
                f"mas ausente em matriz_nutricional"
            ) from exc

        M = np.vstack(linhas)  # shape (n, N_NUTRIENTES)
        assert M.shape[1] == N_NUTRIENTES

        #    Vetor total da formulação = média ponderada das %MS
        #    dos ingredientes pelas suas fracoes. Como fracoes somam
        #    ~1.0 (validado por soma_valida), isso já é diretamente a
        #    %MS da mistura - sem necessidade de dividir por 100 aqui.
        vetor_total_valores = participacao.fracoes @ M  # shape (N_NUTRIENTES,)
        vetor_total = VetorNutricional(valores=vetor_total_valores)


        # Desvios por nutriente configurado -> ResultadoAdequacao

        resultado_adequacao = ResultadoAdequacao.calcular(
            vetor_total=vetor_total,
            requisitos=requisitos,
            soma_participacoes=participacao.soma(),
        )


        # Massa absoluta por ingrediente (kg/dia), para persistência
        # dos campos *_kg de IngredienteFormulacao.

        por_ingrediente: list[ResultadoPorIngrediente] = []
        for idx, id_ingrediente in enumerate(participacao.ids_ingredientes):
            fracao_i = float(participacao.fracoes[idx])
            ms_kg_i = fracao_i * cms_total_kg
            nutrientes_kg_i = VetorNutricional(
                valores=M[idx, :] * PERCENTUAL_PARA_FRACAO * ms_kg_i
            )
            por_ingrediente.append(
                ResultadoPorIngrediente(
                    id_ingrediente=id_ingrediente,
                    fracao_ms=fracao_i,
                    ms_kg=ms_kg_i,
                    nutrientes_kg=nutrientes_kg_i,
                )
            )

        return ResultadoRecalculo(
            resultado_adequacao=resultado_adequacao,
            vetor_total_pct=vetor_total,
            por_ingrediente=tuple(por_ingrediente),
            cms_total_kg=cms_total_kg,
        )