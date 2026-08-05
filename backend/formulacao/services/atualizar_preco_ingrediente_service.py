"""
Application Service - AtualizarPrecoIngredienteService.

Fase 2 (Custos) — Step 5.

Único ponto de decisão sobre "onde gravar o preço": grava no banco de
preços regional do usuário (PrecoIngredienteUsuario) ou apenas no
override local da formulação (IngredienteFormulacao.custo_kg_mn_override),
de acordo com o `escopo` escolhido pelo usuário no frontend. O backend
não pergunta nada em runtime — a pergunta já foi respondida antes da
chamada, via `escopo`.

Fluxo:
  1. Carrega o IngredienteFormulacao com select_for_update, garantindo
     que pertence à formulação informada (evita editar preço de receita
     alheia) e evitando corrida entre duas edições simultâneas.
  2. Resolve o preço anterior (override local, se houver; senão o
     preço regional vigente do usuário) — só para fins de auditoria.
  3. Escreve o novo preço no destino certo:
       escopo="geral"    -> upsert em PrecoIngredienteUsuario(usuario,
                             ingrediente). NÃO grava em Ingrediente.custo_kg
                             — esse campo é compartilhado por todos os
                             usuários do catálogo Valadares; gravar ali
                             vazaria o preço regional de um produtor
                             para o catálogo de todos os outros (ver
                             docstring de PrecoIngredienteUsuario em
                             ingrediente/models.py). O override local
                             DESTE registro é limpo, pois o usuário
                             está dizendo "quero seguir meu banco de
                             preços a partir de agora".
       escopo="receita"  -> IngredienteFormulacao.custo_kg_mn_override
                             (não altera o banco de preços do usuário).
  4. Registra HistoricoPrecoIngrediente (auditoria de preço).
  5. Dispara RecalcularCustoService — recomputa só os indicadores
     econômicos desta formulação. Preço não afeta adequação
     nutricional, então não é necessário rodar o pipeline nutricional
     completo (RecalcularFormulacaoService).
  6. Registra EventoFormulacao (auditoria de eventos de negócio).

Tudo dentro de transaction.atomic.
"""

from __future__ import annotations

from typing import Literal

from django.db import transaction

from formulacao.models import IngredienteFormulacao, OrigemCustoChoices, TipoEvento
from formulacao.repositories import EventoRepository
from formulacao.services.recalcular_custo_service import RecalcularCustoService
from ingrediente.models import (
    HistoricoPrecoIngrediente,
    OrigemAlteracaoPrecoChoices,
    PrecoIngredienteUsuario,
)

Escopo = Literal["receita", "geral"]


class AtualizarPrecoIngredienteService:

    @staticmethod
    @transaction.atomic
    def executar(
        formulacao_id: int,
        ing_form_id: int,
        novo_preco: float,
        escopo: Escopo,
        usuario_id: int | None = None,
    ) -> IngredienteFormulacao:
        if novo_preco is None or novo_preco < 0:
            raise ValueError(
                f"Preço inválido: {novo_preco}. Informe um valor >= 0."
            )
        if escopo not in ("receita", "geral"):
            raise ValueError(
                f"Escopo inválido: {escopo!r}. Use 'receita' ou 'geral'."
            )
        if escopo == "geral" and usuario_id is None:
            raise ValueError(
                "Não é possível atualizar o banco de preços regional "
                "sem um usuário identificado."
            )

        try:
            ing_form = (
                IngredienteFormulacao.objects
                .select_related("ingrediente")
                .select_for_update()
                .get(pk=ing_form_id, formulacao_id=formulacao_id)
            )
        except IngredienteFormulacao.DoesNotExist:
            raise ValueError(
                f"IngredienteFormulacao {ing_form_id} não encontrado "
                f"na formulação {formulacao_id}."
            )

        ingrediente = ing_form.ingrediente
        if ingrediente is None:
            raise ValueError(
                "Não é possível definir preço: o ingrediente desta linha "
                "foi removido do catálogo."
            )

        preco_regional_atual = (
            PrecoIngredienteUsuario.objects
            .filter(usuario_id=usuario_id, ingrediente=ingrediente)
            .values_list("preco_kg_mn", flat=True)
            .first()
        )
        preco_anterior = (
            ing_form.custo_kg_mn_override
            if ing_form.custo_kg_mn_override is not None
            else preco_regional_atual
        )

        if escopo == "geral":
            PrecoIngredienteUsuario.objects.update_or_create(
                usuario_id=usuario_id,
                ingrediente=ingrediente,
                defaults={"preco_kg_mn": novo_preco},
            )
            ing_form.custo_kg_mn_override = None
            ing_form.origem_custo = OrigemCustoChoices.CATALOGO
            origem_alteracao = OrigemAlteracaoPrecoChoices.CATALOGO
        else:
            ing_form.custo_kg_mn_override = novo_preco
            ing_form.origem_custo = OrigemCustoChoices.OVERRIDE_LOCAL
            origem_alteracao = OrigemAlteracaoPrecoChoices.FORMULACAO

        ing_form.save(update_fields=["custo_kg_mn_override", "origem_custo"])

        HistoricoPrecoIngrediente.objects.create(
            ingrediente=ingrediente,
            preco_anterior=preco_anterior,
            preco_novo=novo_preco,
            usuario_id=usuario_id,
            origem_alteracao=origem_alteracao,
        )

        RecalcularCustoService.executar(formulacao_id)

        EventoRepository.registrar(
            formulacao_id=formulacao_id,
            tipo_evento=TipoEvento.PRECO_ATUALIZADO,
            payload={
                "ing_form_id":     ing_form_id,
                "ingrediente_id":  ingrediente.id,
                "escopo":          escopo,
                "preco_anterior":  preco_anterior,
                "preco_novo":      novo_preco,
            },
            usuario_id=usuario_id,
        )

        return ing_form
