"""
Application Service - AjustarParticipacaoService.

Gerencia dois casos de uso relacionados à participação manual:

  1. ajustar(): usuário edita a % MS de um ingrediente.
     - Valida a fração.
     - Registra o valor anterior no EventoFormulacao.
     - Persiste nova fração e marca o ingrediente como MANUAL_TRAVADA.
     - Dispara RecalcularFormulacaoService (recalcula nutrientes,
       gera alertas, cria snapshot).
     - NÃO redistribui os demais ingredientes — isso é
       responsabilidade de AdicionarIngredienteService e
       RemoverIngredienteService (Fase D, redistribuição).

  2. destravar(): usuário devolve o controle do ingrediente ao sistema.
     - Marca origem_participacao como CALCULADA.
     - NÃO altera ms_porcent (o valor travado permanece até a
       próxima redistribuição automática).
     - Dispara RecalcularFormulacaoService (gera novo snapshot
       refletindo a mudança de origem).

Separação de responsabilidades:
  - Validações de domínio (fração fora de [0,1], ingrediente não
    pertence à formulação) → levantam ValueError → view retorna 400.
  - Soma ≠ 100% após ajuste → não bloqueia, apenas gera alerta
    via MotorAlertas dentro do RecalcularFormulacaoService.
"""

from __future__ import annotations

from django.db import transaction

from formulacao.models import IngredienteFormulacao, OrigemParticipacaoChoices, TipoEvento
from formulacao.domain.participacao import OrigemParticipacao
from formulacao.repositories import EventoRepository, IngredienteFormulacaoRepository
from formulacao.services.recalcular_formulacao_service import RecalcularFormulacaoService


class AjustarParticipacaoService:

    @staticmethod
    @transaction.atomic
    def ajustar(
        formulacao_id: int,
        ing_form_id: int,
        nova_fracao: float,
        usuario_id: int | None = None,
    ) -> None:
        """
        Edita manualmente a participação de um ingrediente.

        nova_fracao : valor em 0-1 (o serializer converte de % para fração).
        """
        
        # Validação
        
        if not (0.0 <= nova_fracao <= 1.0):
            raise ValueError(
                f"nova_fracao deve estar entre 0 e 1 (recebido {nova_fracao}). "
                "O serializer deve converter o percentual enviado pelo front."
            )

        ing_form = AjustarParticipacaoService._get_e_validar(
            formulacao_id, ing_form_id
        )

        fracao_anterior = ing_form.ms_porcent / 100.0

        
        # Nenhuma mudança real → encerra sem criar snapshot desnecessário
        
        if abs(nova_fracao - fracao_anterior) < 1e-9:
            return

        
        # Persistir nova participação e travar
        
        IngredienteFormulacaoRepository.atualizar_participacao(
            ing_form_id=ing_form_id,
            fracao=nova_fracao,
            origem=OrigemParticipacao.MANUAL_TRAVADA,
        )

        
        # Registrar evento antes do recálculo
        
        nome_ing = ing_form.ingrediente.nome if ing_form.ingrediente else "(removido)"
        EventoRepository.registrar(
            formulacao_id=formulacao_id,
            tipo_evento=TipoEvento.PARTICIPACAO_EDITADA,
            payload={
                "ing_form_id":       ing_form_id,
                "ingrediente_nome":  nome_ing,
                "fracao_anterior":   round(fracao_anterior, 6),
                "fracao_nova":       round(nova_fracao, 6),
                "pct_anterior":      round(fracao_anterior * 100, 4),
                "pct_nova":          round(nova_fracao * 100, 4),
            },
            usuario_id=usuario_id,
        )

        
        # Recalcular nutrientes + snapshot
        
        nome_ing_curto = nome_ing[:40]
        RecalcularFormulacaoService.executar(
            formulacao_id=formulacao_id,
            usuario_id=usuario_id,
            motivo=f"edição manual: {nome_ing_curto} → {nova_fracao * 100:.1f}%",
        )

    @staticmethod
    @transaction.atomic
    def destravar(
        formulacao_id: int,
        ing_form_id: int,
        usuario_id: int | None = None,
    ) -> None:
        """
        Devolve o controle do ingrediente ao sistema (CALCULADA).

        O ms_porcent atual é mantido — a próxima chamada a
        redistribuir() (via Adicionar/RemoverIngredienteService)
        irá ajustá-lo.
        """
        ing_form = AjustarParticipacaoService._get_e_validar(
            formulacao_id, ing_form_id
        )

        # Já está livre — nada a fazer
        if ing_form.origem_participacao == OrigemParticipacaoChoices.CALCULADA:
            return

        IngredienteFormulacaoRepository.atualizar_participacao(
            ing_form_id=ing_form_id,
            fracao=ing_form.ms_porcent / 100.0,   # mantém valor atual
            origem=OrigemParticipacao.CALCULADA,
        )

        nome_ing = ing_form.ingrediente.nome if ing_form.ingrediente else "(removido)"
        EventoRepository.registrar(
            formulacao_id=formulacao_id,
            tipo_evento=TipoEvento.PARTICIPACAO_DESTRAVADA,
            payload={
                "ing_form_id":      ing_form_id,
                "ingrediente_nome": nome_ing,
                "fracao_atual":     round(ing_form.ms_porcent / 100.0, 6),
            },
            usuario_id=usuario_id,
        )

        RecalcularFormulacaoService.executar(
            formulacao_id=formulacao_id,
            usuario_id=usuario_id,
            motivo=f"destravamento: {nome_ing[:40]}",
        )

    
    # Helper
    

    @staticmethod
    def _get_e_validar(
        formulacao_id: int,
        ing_form_id: int,
    ) -> IngredienteFormulacao:
        """
        Retorna o IngredienteFormulacao garantindo que pertence à
        formulação. Levanta ValueError se não encontrado.
        """
        try:
            return (
                IngredienteFormulacao.objects
                .select_related("ingrediente")
                .get(pk=ing_form_id, formulacao_id=formulacao_id)
            )
        except IngredienteFormulacao.DoesNotExist:
            raise ValueError(
                f"IngredienteFormulacao {ing_form_id} não encontrado "
                f"na formulação {formulacao_id}."
            )