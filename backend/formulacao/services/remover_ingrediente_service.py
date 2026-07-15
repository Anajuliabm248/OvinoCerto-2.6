"""
Application Service - RemoverIngredienteService.

Remove um ingrediente de uma formulação e dispara a redistribuição
automática do espaço liberado entre os ingredientes livres restantes
(seção 11 do documento de arquitetura).

Fluxo:
  1. Valida que o IngredienteFormulacao existe e pertence à formulação.
  2. Bloqueia a remoção do último ingrediente (regra de negócio,
     seção 16: formulação vazia é inválida).
  3. Remove o registro.
  4. Recarrega participação restante.
  5. Chama MotorAdequacao.redistribuir() sobre os livres remanescentes
     (o espaço que era ocupado pelo ingrediente removido é absorvido
     automaticamente, pois a soma_alvo do redistribuir é sempre 1.0
     menos o que está travado).
  6. Aplica as novas frações.
  7. Registra evento INGREDIENTE_REMOVIDO.
  8. Dispara RecalcularFormulacaoService.

Caso especial: se restar apenas 1 ingrediente após a remoção, ele
absorve 100% automaticamente (MotorAdequacao.redistribuir trata isso
como caso trivial).
"""

from __future__ import annotations

from django.db import transaction

from formulacao.engines.motor_adequacao import MotorAdequacao
from formulacao.engines.motor_recalculo import MotorRecalculo
from formulacao.models import IngredienteFormulacao, TipoEvento
from formulacao.repositories import (
    EventoRepository,
    ExigenciaRepository,
    IngredienteFormulacaoRepository,
)
from formulacao.services._configuracao_ingrediente import configuracao_a_partir_do_ingrediente
from formulacao.services.recalcular_formulacao_service import RecalcularFormulacaoService


class RemoverIngredienteService:

    @staticmethod
    @transaction.atomic
    def executar(
        formulacao_id: int,
        ing_form_id: int,
        usuario_id: int | None = None,
    ) -> None:
        # ------------------------------------------------------------------
        # Validações
        # ------------------------------------------------------------------
        try:
            alvo = (
                IngredienteFormulacao.objects
                .select_related("ingrediente")
                .get(pk=ing_form_id, formulacao_id=formulacao_id)
            )
        except IngredienteFormulacao.DoesNotExist:
            raise ValueError(
                f"IngredienteFormulacao {ing_form_id} não encontrado "
                f"na formulação {formulacao_id}."
            )

        total_ingredientes = IngredienteFormulacao.objects.filter(
            formulacao_id=formulacao_id
        ).count()
        if total_ingredientes <= 1:
            raise ValueError(
                "Não é permitido remover o último ingrediente de uma formulação "
                "(formulação vazia é inválida)."
            )

        nome_removido = alvo.ingrediente.nome if alvo.ingrediente else "(removido)"
        fracao_removida = alvo.ms_porcent / 100.0

        # ------------------------------------------------------------------
        # Remover
        # ------------------------------------------------------------------
        alvo.delete()

        # ------------------------------------------------------------------
        # Recarregar participação restante
        # ------------------------------------------------------------------
        participacao = IngredienteFormulacaoRepository.get_participacao(formulacao_id)
        vetores       = IngredienteFormulacaoRepository.get_vetores_nutricionais(formulacao_id)
        requisitos    = ExigenciaRepository.get_requisitos(formulacao_id)

        if not requisitos:
            raise ValueError(
                f"Formulação {formulacao_id} não possui ExigenciaConfigurada."
            )

        matriz_M = MotorRecalculo.montar_matriz(vetores)

        ing_form_qs = list(
            IngredienteFormulacao.objects
            .filter(formulacao_id=formulacao_id)
            .select_related("ingrediente")
            .order_by("id")
        )
        configuracoes = [
            configuracao_a_partir_do_ingrediente(obj.ingrediente)
            for obj in ing_form_qs
        ]

        # ------------------------------------------------------------------
        # Redistribuir o espaço liberado entre os livres remanescentes
        # ------------------------------------------------------------------
        resultado_dist = MotorAdequacao.redistribuir(
            matriz_M=matriz_M,
            requisitos=requisitos,
            participacao_atual=participacao,
            configuracoes=configuracoes,
        )

        ids = participacao.ids_ingredientes
        for pos, remanescente_id in enumerate(ids):
            nova_fracao = float(resultado_dist.fracoes[pos])
            origem_atual = participacao.origens[pos]
            IngredienteFormulacaoRepository.atualizar_participacao(
                ing_form_id=remanescente_id,
                fracao=nova_fracao,
                origem=origem_atual,
            )

        # ------------------------------------------------------------------
        # Evento + recálculo
        # ------------------------------------------------------------------
        EventoRepository.registrar(
            formulacao_id=formulacao_id,
            tipo_evento=TipoEvento.INGREDIENTE_REMOVIDO,
            payload={
                "ing_form_id":       ing_form_id,
                "ingrediente_nome":  nome_removido,
                "fracao_liberada":   round(fracao_removida, 6),
                "convergiu":         resultado_dist.convergiu,
                "mensagem_solver":   resultado_dist.mensagem,
            },
            usuario_id=usuario_id,
        )

        EventoRepository.registrar(
            formulacao_id=formulacao_id,
            tipo_evento=TipoEvento.REDISTRIBUICAO_EXECUTADA,
            payload={
                "motivo":    f"remoção de {nome_removido}",
                "convergiu": resultado_dist.convergiu,
            },
            usuario_id=usuario_id,
        )

        RecalcularFormulacaoService.executar(
            formulacao_id=formulacao_id,
            usuario_id=usuario_id,
            motivo=f"remoção de ingrediente: {nome_removido}",
        )
