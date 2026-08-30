"""Caso de uso para fixar ou liberar o percentual total de volumoso."""

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
from formulacao.services._percentual_volumoso import (
    percentual_volumoso_aplicado,
    resolver_configuracao_volumoso,
)
from formulacao.services.recalcular_formulacao_service import RecalcularFormulacaoService


class AtualizarPercentualVolumosoService:
    """Atualiza modo/configuracao sem confundir travas individuais."""

    @staticmethod
    @transaction.atomic
    def executar(
        formulacao_id: int,
        percentual_alvo_volumoso: float | None = None,
        modo_percentual_volumoso: str | None = None,
        usuario_id: int | None = None,
    ) -> Formulacao:
        try:
            formulacao = Formulacao.objects.select_for_update().get(pk=formulacao_id)
        except Formulacao.DoesNotExist:
            raise ValueError(f"Formulação {formulacao_id} não encontrada.") from None

        modo_novo, percentual_fixo, origem_nova = resolver_configuracao_volumoso(
            formulacao=formulacao,
            modo_solicitado=modo_percentual_volumoso,
            percentual_solicitado=percentual_alvo_volumoso,
        )

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
            percentual_alvo_volumoso=percentual_fixo,
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

        percentual_aplicado_novo = percentual_volumoso_aplicado(
            resultado.fracoes,
            configuracoes,
        )
        if (
            percentual_fixo is not None
            and abs(percentual_aplicado_novo - percentual_fixo) > 1e-9
        ):
            raise RuntimeError(
                "Falha interna: o resultado nao respeitou o percentual fixo de volumoso."
            )

        estado_anterior = {
            "modo": formulacao.modo_percentual_volumoso,
            "percentual_alvo": formulacao.percentual_alvo_volumoso,
            "percentual_aplicado": formulacao.percentual_volumoso_aplicado,
            "origem": formulacao.origem_percentual_volumoso,
        }
        formulacao.modo_percentual_volumoso = modo_novo
        formulacao.percentual_alvo_volumoso = percentual_fixo
        formulacao.percentual_volumoso_aplicado = percentual_aplicado_novo
        formulacao.origem_percentual_volumoso = origem_nova
        formulacao.save(update_fields=[
            "modo_percentual_volumoso",
            "percentual_alvo_volumoso",
            "percentual_volumoso_aplicado",
            "origem_percentual_volumoso",
        ])

        motivo = (
            "alteracao da definicao do percentual de volumoso: "
            f"{estado_anterior['modo']} -> {modo_novo}; aplicado "
            f"{estado_anterior['percentual_aplicado'] * 100:.2f}% -> "
            f"{percentual_aplicado_novo * 100:.2f}%"
        )
        saida_recalculo = RecalcularFormulacaoService.executar(
            formulacao_id=formulacao_id,
            usuario_id=usuario_id,
            motivo=motivo,
        )
        EventoRepository.registrar(
            formulacao_id=formulacao_id,
            tipo_evento=TipoEvento.PERCENTUAL_VOLUMOSO_ALTERADO,
            payload={
                "estado_anterior": estado_anterior,
                "percentual_anterior": estado_anterior["percentual_alvo"],
                "percentual_novo": percentual_fixo,
                "modo_novo": modo_novo,
                "percentual_alvo_novo": percentual_fixo,
                "percentual_aplicado_novo": percentual_aplicado_novo,
                "origem_nova": origem_nova,
                "convergiu": resultado.convergiu,
                "mensagem_solver": resultado.mensagem,
                "adequacao_nutricional_completa": (
                    bool(saida_recalculo.resultado.atende_tudo)
                ),
            },
            usuario_id=usuario_id,
        )
        return Formulacao.objects.get(pk=formulacao_id)
