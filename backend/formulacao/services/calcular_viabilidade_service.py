"""
Application Service - CalcularViabilidadeService.

Fase 2 (Custos) — Quadros 9-14 ("Custos e Viabilidade da Dieta").

Cálculo AO VIVO, sem persistência de resultado — mesmo padrão do
endpoint GET /formulacoes/{id}/custos/. Só ParametrosViabilidade
(input) é persistido; a saída do MotorViabilidade é sempre recomputada
na hora, então nunca fica desatualizada em relação à participação
atual da formulação ou ao preço vigente dos ingredientes.

Reaproveita os mesmos dados já resolvidos para o Quadro de custo
simples (IngredienteFormulacaoRepository.get_participacao/
get_dados_custo) — participação %MS, MS% por ingrediente e preço já
resolvido (override de receita > banco regional do usuário > 0.0).
Não recalcula nada disso; MotorViabilidade só consome.
"""

from __future__ import annotations

from formulacao.domain.participacao import ParticipacaoVetor
from formulacao.engines.motor_viabilidade import (
    MotorViabilidade,
    ParametrosViabilidade as ParametrosViabilidadeVO,
    SaidaViabilidade,
)
from formulacao.repositories import (
    IngredienteFormulacaoRepository,
    ParametrosViabilidadeRepository,
)


class CalcularViabilidadeService:
    """Monta os vetores da receita e executa a projeção econômica atual."""

    @staticmethod
    def executar(
        formulacao_id: int,
        incluir_quadros_economicos: bool = True,
    ) -> SaidaViabilidade:
        """Calcula custos para todos os ovinos e economia apenas quando aplicável."""
        participacao: ParticipacaoVetor = IngredienteFormulacaoRepository.get_participacao(
            formulacao_id
        )
        if len(participacao) == 0:
            raise ValueError(
                f"Formulação {formulacao_id} não possui ingredientes."
            )

        custos_kg_mn, ms_percentuais = IngredienteFormulacaoRepository.get_dados_custo(
            formulacao_id
        )
        nomes, ingrediente_ids = IngredienteFormulacaoRepository.get_nomes_e_ids(
            formulacao_id
        )

        parametros_db = ParametrosViabilidadeRepository.get_ou_criar_default(formulacao_id)
        parametros_vo = ParametrosViabilidadeVO(
            num_animais=parametros_db.num_animais,
            gmd_esperado_kg=parametros_db.gmd_esperado_kg,
            estimativa_permanencia_dias=parametros_db.estimativa_permanencia_dias,
            peso_entrada_kg=parametros_db.peso_entrada_kg,
            cms_percentual_pv=parametros_db.cms_percentual_pv,
            perdas_alimentos_percentual=parametros_db.perdas_alimentos_percentual,
            preco_venda_kg_pv=(
                parametros_db.preco_venda_kg_pv
                if incluir_quadros_economicos else None
            ),
        )

        return MotorViabilidade.calcular(
            parametros=parametros_vo,
            fracoes_ms=participacao.fracoes,
            ms_percentuais=ms_percentuais,
            precos_kg_mn=custos_kg_mn,
            nomes=nomes,
            ingrediente_ids=ingrediente_ids,
        )
