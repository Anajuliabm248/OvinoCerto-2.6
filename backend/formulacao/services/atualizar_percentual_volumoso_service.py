"""Caso de uso para alterar o alvo rígido de volumosos da formulação."""

from __future__ import annotations

from django.db import transaction

from formulacao.engines.motor_adequacao import MotorAdequacao
from formulacao.engines.motor_recalculo import MotorRecalculo
from formulacao.models import (
    ExigenciaConfigurada,
    Formulacao,
    IngredienteFormulacao,
    TipoEvento,
)
from formulacao.repositories import (
    EventoRepository,
    ExigenciaRepository,
    IngredienteFormulacaoRepository,
    ReferenciaSuplementoRepository,
)
from formulacao.services._configuracao_ingrediente import configuracao_a_partir_do_ingrediente
from formulacao.services.recalcular_formulacao_service import RecalcularFormulacaoService


class AtualizarPercentualVolumosoService:
    """Atualiza o alvo e redistribui sem criar uma nova geração inicial."""

    @staticmethod
    @transaction.atomic
    def executar(
        formulacao_id: int,
        percentual_alvo_volumoso: float,
        usuario_id: int | None = None,
    ) -> Formulacao:
        if not 0.0 <= percentual_alvo_volumoso <= 1.0:
            raise ValueError("O percentual de volumoso deve estar entre 0% e 100%.")

        try:
            formulacao = Formulacao.objects.select_for_update().get(pk=formulacao_id)
        except Formulacao.DoesNotExist:
            raise ValueError(f"Formulação {formulacao_id} não encontrada.") from None

        if not ExigenciaConfigurada.objects.filter(formulacao_id=formulacao_id).exists():
            raise ValueError(
                f"Formulação {formulacao_id} não possui ExigenciaConfigurada."
            )

        participacao = IngredienteFormulacaoRepository.get_participacao(formulacao_id)
        if len(participacao) == 0:
            raise ValueError("Selecione ao menos um ingrediente antes de alterar o alvo.")

        vetores = IngredienteFormulacaoRepository.get_vetores_nutricionais(formulacao_id)
        requisitos = ExigenciaRepository.get_requisitos(formulacao_id)
        contexto_zootecnico = ExigenciaRepository.get_contexto_zootecnico(formulacao_id)
        matriz_M = MotorRecalculo.montar_matriz(vetores)
        ingredientes_formulacao = list(
            IngredienteFormulacao.objects
            .filter(formulacao_id=formulacao_id)
            .select_related("ingrediente")
            .order_by("id")
        )
        configuracoes = [
            configuracao_a_partir_do_ingrediente(item.ingrediente)
            for item in ingredientes_formulacao
        ]

        resultado = MotorAdequacao.redistribuir(
            matriz_M=matriz_M,
            requisitos=requisitos,
            participacao_atual=participacao,
            configuracoes=configuracoes,
            percentual_alvo_volumoso=percentual_alvo_volumoso,
            reiniciar_livres=True,
            contexto_zootecnico=contexto_zootecnico,
            referencias_suplemento=ReferenciaSuplementoRepository.listar_ativas(),
        )

        for posicao, ing_form_id in enumerate(participacao.ids_ingredientes):
            IngredienteFormulacaoRepository.atualizar_participacao(
                ing_form_id=ing_form_id,
                fracao=float(resultado.fracoes[posicao]),
                origem=participacao.origens[posicao],
            )

        percentual_anterior = formulacao.percentual_alvo_volumoso
        formulacao.percentual_alvo_volumoso = percentual_alvo_volumoso
        formulacao.save(update_fields=["percentual_alvo_volumoso"])

        motivo = (
            "alteração do percentual de volumoso: "
            f"{percentual_anterior * 100:.2f}% → {percentual_alvo_volumoso * 100:.2f}%"
        )
        RecalcularFormulacaoService.executar(
            formulacao_id=formulacao_id,
            usuario_id=usuario_id,
            motivo=motivo,
        )
        EventoRepository.registrar(
            formulacao_id=formulacao_id,
            tipo_evento=TipoEvento.PERCENTUAL_VOLUMOSO_ALTERADO,
            payload={
                "percentual_anterior": percentual_anterior,
                "percentual_novo": percentual_alvo_volumoso,
                "convergiu": resultado.convergiu,
                "mensagem_solver": resultado.mensagem,
            },
            usuario_id=usuario_id,
        )
        return Formulacao.objects.get(pk=formulacao_id)
