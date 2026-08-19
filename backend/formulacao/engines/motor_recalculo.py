"""
Domínio puro - MotorRecalculo.

Pipeline determinístico que transforma participações (%MS) em
ResultadoAdequacao. Sem I/O, sem Django, sem efeitos colaterais.

Sequência (seção 7 do documento de arquitetura):
  1. Recebe ParticipacaoVetor + matriz nutricional M + requisitos + CMS
  2. Calcula ms_kg por ingrediente
  3. Multiplica pela matriz nutricional -> nutriente_kg por ingrediente
  4. Agrega totais -> VetorNutricional da formulação (% da MS)
  5. Compara contra requisitos -> DesvioNutricional por nutriente
  6. Monta ResultadoAdequacao

Por ser idempotente e puro, pode ser chamado quantas vezes necessário
sem alterar estado — essencial para testes unitários e para o modo
"simulação" do MotorSugestao (what-if sem persistir).

Invariante de escala (crítico):
  fracoes em ParticipacaoVetor são 0-1 (não 0-100).
  valores em M são % da MS (ex.: PB=18.5, não 0.185).
  A multiplicação fracoes * M[i] produz a contribuição de cada
  ingrediente em % da MS — sem nenhuma conversão de escala adicional.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from formulacao.domain.nutrientes import N_NUTRIENTES, Nutriente, indice_de
from formulacao.domain.participacao import ParticipacaoVetor
from formulacao.domain.requisito import RequisitoNutriente
from formulacao.domain.resultado import ResultadoAdequacao
from formulacao.domain.vetor_nutricional import VetorNutricional


@dataclass(frozen=True)
class EntradaRecalculo:
    """
    Agrupa todas as entradas do MotorRecalculo.

    participacao : ParticipacaoVetor com fracoes 0-1.
    matriz_M     : np.ndarray shape (n_ingredientes, N_NUTRIENTES),
                   valores em % da MS (ex.: PB=18.5),
                   na mesma ordem de ids_ingredientes e de NUTRIENTES_ORDEM.
    requisitos   : dict {Nutriente: RequisitoNutriente}, vindo da
                   ExigenciaConfigurada.
    cms_kg       : Consumo de Matéria Seca total do lote (kg/dia).
                   Usado para converter % MS -> kg absolutos por ingrediente.
    """

    participacao: ParticipacaoVetor
    matriz_M: np.ndarray
    requisitos: dict[Nutriente, RequisitoNutriente]
    cms_kg: float

    def __post_init__(self) -> None:
        n = len(self.participacao)
        if self.matriz_M.shape != (n, N_NUTRIENTES):
            raise ValueError(
                f"EntradaRecalculo: matriz_M tem shape {self.matriz_M.shape}, "
                f"esperado ({n}, {N_NUTRIENTES}). "
                f"Cada linha = um ingrediente, cada coluna = um nutriente "
                f"na ordem de NUTRIENTES_ORDEM."
            )
        if self.cms_kg <= 0:
            raise ValueError(
                f"EntradaRecalculo: cms_kg deve ser positivo, recebido {self.cms_kg}"
            )


@dataclass(frozen=True)
class SaidaRecalculo:
    """
    Saída completa do MotorRecalculo.

    resultado           : ResultadoAdequacao (desvios + soma).
    vetor_total         : VetorNutricional agregado da formulação (% MS).
    contribuicoes_kg    : np.ndarray shape (n_ingredientes, N_NUTRIENTES)
                          — kg de cada nutriente fornecido por cada
                          ingrediente por dia. Usado pelo repositório
                          para persistir os campos *_kg em
                          IngredienteFormulacao.
    ms_kg_ingredientes  : np.ndarray shape (n_ingredientes,)
                          — kg de MS por ingrediente por dia.
    """

    resultado: ResultadoAdequacao
    vetor_total: VetorNutricional
    contribuicoes_kg: np.ndarray
    ms_kg_ingredientes: np.ndarray


class MotorRecalculo:
    """
    Serviço de domínio puro. Nenhuma instância de estado — todos os
    métodos são estáticos para deixar explícito que não há efeito
    colateral.
    """

    @staticmethod
    def calcular(entrada: EntradaRecalculo) -> SaidaRecalculo:
        """
        Executa o pipeline completo de recálculo.

        Chamado por:
        - Application services após edição manual de participação.
        - MotorAdequacao após gerar/redistribuir participações.
        - MotorSugestao em modo simulação (what-if).
        """
        participacao = entrada.participacao
        M = entrada.matriz_M
        cms_kg = entrada.cms_kg

        
        # Passo 2: ms_kg por ingrediente
        # fracoes[i] * cms_kg = kg de MS que o ingrediente i contribui/dia
        
        ms_kg_ing = participacao.fracoes * cms_kg  # shape (n,)

        
        # Passo 3: nutriente_kg por ingrediente
        # ms_kg_ing[i] * M[i, :] / 100 = kg de cada nutriente do ing i/dia
        # M está em % da MS, por isso dividimos por 100 para obter fração.
        
        contribuicoes_kg = (ms_kg_ing[:, np.newaxis] * M) / 100.0  # shape (n, N_NUTRIENTES)

        
        # Passo 4: totais em kg/dia -> converter de volta para % da MS
        # total_nutriente_kg / cms_kg * 100 = % da MS da formulação
        
        total_kg = contribuicoes_kg.sum(axis=0)  # shape (N_NUTRIENTES,)
        total_pct = (total_kg / cms_kg) * 100.0  # shape (N_NUTRIENTES,)

        idx_ca = indice_de(Nutriente.CA)
        idx_p = indice_de(Nutriente.P)
        idx_ca_p = indice_de(Nutriente.CA_P)
        total_pct[idx_ca_p] = (
            total_pct[idx_ca] / total_pct[idx_p]
            if total_pct[idx_p] > 1e-12
            else 0.0
        )

        vetor_total = VetorNutricional(valores=total_pct)

        
        # Passo 5-6: desvios por nutriente
        
        resultado = ResultadoAdequacao.calcular(
            vetor_total=vetor_total,
            requisitos=entrada.requisitos,
            soma_participacoes=participacao.soma(),
        )

        return SaidaRecalculo(
            resultado=resultado,
            vetor_total=vetor_total,
            contribuicoes_kg=contribuicoes_kg,
            ms_kg_ingredientes=ms_kg_ing,
        )

    @staticmethod
    def montar_matriz(vetores: list[VetorNutricional]) -> np.ndarray:
        """
        Converte uma lista de VetorNutricional (um por ingrediente)
        na matriz M usada pelo pipeline.

        Shape resultante: (n_ingredientes, N_NUTRIENTES).
        Mantido como utilitário aqui para que repositórios e testes
        não precisem saber da ordem interna de NUTRIENTES_ORDEM.
        """
        if not vetores:
            return np.empty((0, N_NUTRIENTES), dtype=float)
        return np.vstack([v.valores for v in vetores])  # shape (n, N_NUTRIENTES)
