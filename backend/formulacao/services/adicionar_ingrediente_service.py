"""
Application Service - AdicionarIngredienteService.

Adiciona um novo ingrediente a uma formulação existente e dispara
a redistribuição automática de %MS entre os ingredientes livres
(seção 11 do documento de arquitetura).

Fluxo:
  1. Valida que o ingrediente existe e ainda não está na formulação.
  2. Cria IngredienteFormulacao com ms_porcent=0, CALCULADA.
  3. Recarrega participação completa (agora incluindo o novo, com
     fração 0 — entra como ingrediente livre).
  4. Chama MotorAdequacao.redistribuir() sobre os livres.
  5. Aplica as novas frações (apenas dos ingredientes CALCULADA;
     os MANUAL_TRAVADA permanecem intocados).
  6. Registra evento INGREDIENTE_ADICIONADO.
  7. Dispara RecalcularFormulacaoService (nutrientes + alertas + snapshot).

Metas nutricionais não atendidas geram alertas. Incompatibilidades
estruturais (soma e limites de participação) rejeitam toda a operação;
como o serviço é atômico, o ingrediente não fica parcialmente adicionado.
"""

from __future__ import annotations

from django.db import transaction

from formulacao.engines.motor_adequacao import MotorAdequacao
from formulacao.engines.motor_recalculo import MotorRecalculo
from formulacao.models import (
    Formulacao,
    IngredienteFormulacao,
    OrigemParticipacaoChoices,
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


class AdicionarIngredienteService:
    """Inclui um ingrediente e redistribui as linhas livres para manter 100%."""

    @staticmethod
    @transaction.atomic
    def executar(
        formulacao_id: int,
        ingrediente_id: int,
        usuario_id: int | None = None,
    ) -> IngredienteFormulacao:
        """
        Retorna o IngredienteFormulacao recém-criado (já com ms_porcent
        atualizado pela redistribuição).
        """
        # ------------------------------------------------------------------
        # Validações
        # ------------------------------------------------------------------
        if IngredienteFormulacao.objects.filter(
            formulacao_id=formulacao_id, ingrediente_id=ingrediente_id
        ).exists():
            raise ValueError(
                f"Ingrediente {ingrediente_id} já está na formulação {formulacao_id}."
            )

        try:
            ingrediente = Ingrediente.objects.get(pk=ingrediente_id)
        except Ingrediente.DoesNotExist:
            raise ValueError(f"Ingrediente {ingrediente_id} não encontrado.")

        # ------------------------------------------------------------------
        # Criar o registro com participação zero, livre
        # ------------------------------------------------------------------
        novo = IngredienteFormulacao.objects.create(
            formulacao_id=formulacao_id,
            ingrediente=ingrediente,
            ms_porcent=0.0,
            origem_participacao=OrigemParticipacaoChoices.CALCULADA,
        )

        # ------------------------------------------------------------------
        # Recarregar estado completo (agora com o novo ingrediente)
        # ------------------------------------------------------------------
        participacao = IngredienteFormulacaoRepository.get_participacao(formulacao_id)
        vetores       = IngredienteFormulacaoRepository.get_vetores_nutricionais(formulacao_id)
        requisitos    = ExigenciaRepository.get_requisitos(formulacao_id)

        if not requisitos:
            raise ValueError(
                f"Formulação {formulacao_id} não possui ExigenciaConfigurada."
            )

        matriz_M = MotorRecalculo.montar_matriz(vetores)

        # Configurações de classificação na mesma ordem de participacao
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
        # Redistribuir entre os livres (inclui o novo ingrediente)
        # ------------------------------------------------------------------
        resultado_dist = MotorAdequacao.redistribuir(
            matriz_M=matriz_M,
            requisitos=requisitos,
            participacao_atual=participacao,
            configuracoes=configuracoes,
            percentual_alvo_volumoso=Formulacao.objects.values_list(
                "percentual_alvo_volumoso", flat=True
            ).get(pk=formulacao_id),
        )

        # ------------------------------------------------------------------
        # Aplicar novas frações apenas nos ingredientes CALCULADA
        # (os MANUAL_TRAVADA já vêm intocados de MotorAdequacao.redistribuir)
        # ------------------------------------------------------------------
        ids = participacao.ids_ingredientes
        for pos, ing_form_id in enumerate(ids):
            nova_fracao = float(resultado_dist.fracoes[pos])
            origem_atual = participacao.origens[pos]
            IngredienteFormulacaoRepository.atualizar_participacao(
                ing_form_id=ing_form_id,
                fracao=nova_fracao,
                origem=origem_atual,  # preserva a origem original (travado continua travado)
            )

        # ------------------------------------------------------------------
        # Evento + recálculo
        # ------------------------------------------------------------------
        EventoRepository.registrar(
            formulacao_id=formulacao_id,
            tipo_evento=TipoEvento.INGREDIENTE_ADICIONADO,
            payload={
                "ingrediente_id":   ingrediente_id,
                "ingrediente_nome": ingrediente.nome,
                "convergiu":        resultado_dist.convergiu,
                "mensagem_solver":  resultado_dist.mensagem,
            },
            usuario_id=usuario_id,
        )

        EventoRepository.registrar(
            formulacao_id=formulacao_id,
            tipo_evento=TipoEvento.REDISTRIBUICAO_EXECUTADA,
            payload={
                "motivo":    f"adição de {ingrediente.nome}",
                "convergiu": resultado_dist.convergiu,
            },
            usuario_id=usuario_id,
        )

        RecalcularFormulacaoService.executar(
            formulacao_id=formulacao_id,
            usuario_id=usuario_id,
            motivo=f"adição de ingrediente: {ingrediente.nome}",
        )

        novo.refresh_from_db()
        return novo
