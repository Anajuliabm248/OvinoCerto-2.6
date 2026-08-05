"""
Application Service - RecalcularCustoService.

Fase 2 (Custos) — recomputa APENAS os indicadores econômicos de uma
formulação (custo_ms_kg, custo_mn_kg, custo_animal_dia, custo_lote_dia),
sem tocar em adequação nutricional.

Por que é um service separado de RecalcularFormulacaoService:
custo é um agregado ortogonal à adequação nutricional (documento de
arquitetura, seção 2.4/19 — custo fica "congelado" fora do motor de
adequação). Qualquer alteração de preço não deveria disparar um
recálculo nutricional completo (SLSQP/nnls, alertas, snapshot) — é
caro e desnecessário. Este service é a unidade mínima de trabalho.

Quando o Step 6 integrar custo ao pipeline principal, este service
passa a ser chamado de dentro de RecalcularFormulacaoService.executar()
(mesma participação já carregada, sem query duplicada) — a lógica
aqui não muda, só quem a invoca.
"""

from __future__ import annotations

from formulacao.engines.motor_custo import EntradaCusto, MotorCusto, SaidaCusto
from formulacao.repositories import ExigenciaRepository, IngredienteFormulacaoRepository


class RecalcularCustoService:

    @staticmethod
    def executar(formulacao_id: int) -> SaidaCusto:
        """
        Carrega participação + preços + CMS + número de animais,
        executa o MotorCusto e persiste o resultado.

        Não falha se não houver preço cadastrado — MotorCusto trata
        ingrediente sem preço como custo 0.0 e sinaliza
        `tem_ingrediente_sem_preco=True` na saída, para o MotorAlertas
        (integração prevista no Step 6/7).
        """
        participacao = IngredienteFormulacaoRepository.get_participacao(formulacao_id)
        if len(participacao) == 0:
            raise ValueError(
                f"Formulação {formulacao_id} não possui ingredientes."
            )

        cms_kg = ExigenciaRepository.get_cms_kg(formulacao_id)
        if cms_kg is None or cms_kg <= 0:
            raise ValueError(
                f"CMS inválido para formulação {formulacao_id}: {cms_kg}. "
                "Verifique a ExigenciaConfigurada."
            )

        custos_kg_mn, ms_percentuais = IngredienteFormulacaoRepository.get_dados_custo(
            formulacao_id
        )
        num_animais = IngredienteFormulacaoRepository.get_num_animais(formulacao_id)

        entrada = EntradaCusto(
            fracoes_ms=participacao.fracoes,
            custos_kg_mn=custos_kg_mn,
            ms_percentuais=ms_percentuais,
            cms_total_kg=cms_kg,
            num_animais=num_animais,
        )
        saida = MotorCusto.calcular(entrada)

        IngredienteFormulacaoRepository.salvar_saida_custo(
            formulacao_id=formulacao_id,
            ids_ingredientes=participacao.ids_ingredientes,
            saida=saida,
        )

        return saida
