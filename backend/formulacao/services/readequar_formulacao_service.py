"""Caso de uso para rebalancear uma formulação contra a exigência vigente."""

from __future__ import annotations

from django.db import transaction

from formulacao.domain.participacao import OrigemParticipacao
from formulacao.engines.motor_adequacao import MotorAdequacao, ResultadoDistribuicao
from formulacao.engines.motor_recalculo import MotorRecalculo
from formulacao.models import Formulacao, IngredienteFormulacao, TipoEvento
from formulacao.repositories import (
    EventoRepository,
    ExigenciaRepository,
    IngredienteFormulacaoRepository,
    ReferenciaSuplementoRepository,
)
from formulacao.services._configuracao_ingrediente import (
    configuracao_a_partir_do_ingrediente,
)
from formulacao.services._percentual_volumoso import (
    obter_alvo_volumoso_para_motor,
    percentual_volumoso_aplicado,
)
from formulacao.services.recalcular_formulacao_service import (
    RecalcularFormulacaoService,
)

# pylint: disable=no-member, too-few-public-methods


class ReadequarFormulacaoService:
    """Redistribui ingredientes livres e recalcula o agregado completo."""

    @staticmethod
    @transaction.atomic
    def executar(
        formulacao_id: int,
        usuario_id: int | None = None,
    ) -> ResultadoDistribuicao:
        """Aplica a exigência atual sem recriar a formulação ou romper travas."""
        try:
            formulacao = Formulacao.objects.select_for_update().get(pk=formulacao_id)
        except Formulacao.DoesNotExist:
            raise ValueError(f"Formulação {formulacao_id} não encontrada.") from None

        participacao = IngredienteFormulacaoRepository.get_participacao(formulacao_id)
        if len(participacao) == 0:
            raise ValueError(f"Formulação {formulacao_id} não possui ingredientes.")

        requisitos = ExigenciaRepository.get_requisitos(formulacao_id)
        if not requisitos:
            raise ValueError(
                f"Formulação {formulacao_id} não possui ExigenciaConfigurada."
            )

        vetores = IngredienteFormulacaoRepository.get_vetores_nutricionais(
            formulacao_id
        )
        contexto_zootecnico = ExigenciaRepository.get_contexto_zootecnico(
            formulacao_id
        )
        ingredientes_formulacao = list(
            IngredienteFormulacao.objects.filter(formulacao_id=formulacao_id)
            .select_related("ingrediente")
            .order_by("id")
        )
        configuracoes = [
            configuracao_a_partir_do_ingrediente(item.ingrediente)
            for item in ingredientes_formulacao
        ]

        resultado = MotorAdequacao.redistribuir(
            matriz_M=MotorRecalculo.montar_matriz(vetores),
            requisitos=requisitos,
            participacao_atual=participacao,
            configuracoes=configuracoes,
            percentual_alvo_volumoso=obter_alvo_volumoso_para_motor(
                formulacao_id
            ),
            reiniciar_livres=True,
            contexto_zootecnico=contexto_zootecnico,
            referencias_suplemento=ReferenciaSuplementoRepository.listar_ativas(),
        )

        for posicao, ing_form_id in enumerate(participacao.ids_ingredientes):
            origem = participacao.origens[posicao]
            if origem != OrigemParticipacao.CALCULADA:
                continue
            IngredienteFormulacaoRepository.atualizar_participacao(
                ing_form_id=ing_form_id,
                fracao=float(resultado.fracoes[posicao]),
                origem=origem,
            )

        percentual_aplicado = percentual_volumoso_aplicado(
            resultado.fracoes,
            configuracoes,
        )
        if (
            formulacao.percentual_volumoso_para_motor is not None
            and abs(
                percentual_aplicado - formulacao.percentual_volumoso_para_motor
            )
            > 1e-9
        ):
            raise RuntimeError(
                "Falha interna: o recálculo não respeitou o percentual fixo "
                "de volumoso."
            )

        saida_recalculo = RecalcularFormulacaoService.executar(
            formulacao_id=formulacao_id,
            usuario_id=usuario_id,
            motivo="readequação explícita à exigência vigente",
        )
        EventoRepository.registrar(
            formulacao_id=formulacao_id,
            tipo_evento=TipoEvento.REDISTRIBUICAO_EXECUTADA,
            payload={
                "motivo": "recálculo explícito após alteração de exigência",
                "convergiu": resultado.convergiu,
                "mensagem_solver": resultado.mensagem,
                "percentual_volumoso_aplicado": percentual_aplicado,
                "adequacao_nutricional_completa": bool(
                    saida_recalculo.resultado.atende_tudo
                ),
            },
            usuario_id=usuario_id,
        )
        return resultado
