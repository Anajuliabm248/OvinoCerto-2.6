"""
Application Service - GerarFormulacaoInicialService.

Gera ou regenera a distribuicao de uma formulacao. A fonte principal de
ingredientes e sempre a lista ja vinculada a formulacao; `ingrediente_ids`
existe apenas como compatibilidade para formulacoes ainda vazias.

Fluxo:
  1. Se a formulacao ainda nao tem ingredientes, cria os vinculos enviados
     em `ingrediente_ids` com ms_porcent=0 e origem CALCULADA.
  2. Recarrega as participacoes atuais.
  3. Redistribui os ingredientes CALCULADA do zero, respeitando os
     MANUAL_TRAVADA e o percentual-alvo de volumoso.
  4. Recalcula nutrientes, alertas e snapshot.
  5. Promove a formulacao para ATIVA.
"""

from __future__ import annotations

from django.db import transaction

from formulacao.engines.motor_adequacao import MotorAdequacao
from formulacao.engines.motor_recalculo import MotorRecalculo
from formulacao.models import (
    ExigenciaConfigurada,
    Formulacao,
    IngredienteFormulacao,
    OrigemParticipacaoChoices,
    StatusFormulacao,
    TipoEvento,
)
from formulacao.repositories import (
    EventoRepository,
    ExigenciaRepository,
    IngredienteFormulacaoRepository,
)
from formulacao.services._configuracao_ingrediente import configuracao_a_partir_do_ingrediente
from formulacao.services.recalcular_formulacao_service import RecalcularFormulacaoService
from ingrediente.models import Ingrediente


class GerarFormulacaoInicialService:

    @staticmethod
    @transaction.atomic
    def executar(
        formulacao_id: int,
        ingrediente_ids: list[int],
        usuario_id: int | None = None,
        percentual_alvo_volumoso: float = 0.50,
    ) -> Formulacao:
        formulacao = Formulacao.objects.get(pk=formulacao_id)

        if not ExigenciaConfigurada.objects.filter(formulacao_id=formulacao_id).exists():
            raise ValueError(
                f"Formulacao {formulacao_id} nao possui ExigenciaConfigurada. "
                "Chame IniciarFormulacaoService primeiro."
            )

        usou_ingredientes_existentes = IngredienteFormulacao.objects.filter(
            formulacao_id=formulacao_id
        ).exists()

        if not usou_ingredientes_existentes:
            GerarFormulacaoInicialService._criar_ingredientes_iniciais(
                formulacao=formulacao,
                ingrediente_ids=ingrediente_ids,
            )

        participacao = IngredienteFormulacaoRepository.get_participacao(formulacao_id)
        vetores = IngredienteFormulacaoRepository.get_vetores_nutricionais(formulacao_id)
        requisitos = ExigenciaRepository.get_requisitos(formulacao_id)

        if not requisitos:
            raise ValueError(f"Formulacao {formulacao_id} nao possui ExigenciaConfigurada.")

        ing_form_qs = list(
            IngredienteFormulacao.objects
            .filter(formulacao_id=formulacao_id)
            .select_related("ingrediente")
            .order_by("id")
        )
        if not ing_form_qs:
            raise ValueError("Selecione ao menos um ingrediente.")

        matriz_M = MotorRecalculo.montar_matriz(vetores)
        configuracoes = [
            configuracao_a_partir_do_ingrediente(obj.ingrediente)
            for obj in ing_form_qs
        ]

        resultado_dist = MotorAdequacao.redistribuir(
            matriz_M=matriz_M,
            requisitos=requisitos,
            participacao_atual=participacao,
            configuracoes=configuracoes,
            percentual_alvo_volumoso=percentual_alvo_volumoso,
            reiniciar_livres=True,
        )

        for pos, ing_form_id in enumerate(participacao.ids_ingredientes):
            IngredienteFormulacaoRepository.atualizar_participacao(
                ing_form_id=ing_form_id,
                fracao=float(resultado_dist.fracoes[pos]),
                origem=participacao.origens[pos],
            )

        motivo = (
            "geracao inicial"
            if resultado_dist.convergiu
            else f"geracao inicial (fallback: {resultado_dist.mensagem})"
        )
        RecalcularFormulacaoService.executar(
            formulacao_id=formulacao_id,
            usuario_id=usuario_id,
            motivo=motivo,
        )

        EventoRepository.registrar(
            formulacao_id=formulacao_id,
            tipo_evento=TipoEvento.CRIACAO,
            payload={
                "n_ingredientes": len(ing_form_qs),
                "convergiu": resultado_dist.convergiu,
                "mensagem_solver": resultado_dist.mensagem,
                "percentual_alvo_vol": percentual_alvo_volumoso,
                "usou_ingredientes_existentes": usou_ingredientes_existentes,
            },
            usuario_id=usuario_id,
        )

        formulacao.status = StatusFormulacao.ATIVA
        formulacao.save(update_fields=["status"])

        return formulacao

    @staticmethod
    def _criar_ingredientes_iniciais(
        formulacao: Formulacao,
        ingrediente_ids: list[int],
    ) -> None:
        if not ingrediente_ids:
            raise ValueError("Selecione ao menos um ingrediente.")

        ingredientes = list(Ingrediente.objects.filter(pk__in=ingrediente_ids))
        if len(ingredientes) != len(ingrediente_ids):
            faltando = set(ingrediente_ids) - {i.pk for i in ingredientes}
            raise ValueError(f"Ingredientes nao encontrados: {faltando}")

        ordem = {id_: pos for pos, id_ in enumerate(ingrediente_ids)}
        ingredientes.sort(key=lambda ingrediente: ordem[ingrediente.pk])

        IngredienteFormulacao.objects.bulk_create([
            IngredienteFormulacao(
                formulacao=formulacao,
                ingrediente=ingrediente,
                ms_porcent=0.0,
                origem_participacao=OrigemParticipacaoChoices.CALCULADA,
            )
            for ingrediente in ingredientes
        ])
