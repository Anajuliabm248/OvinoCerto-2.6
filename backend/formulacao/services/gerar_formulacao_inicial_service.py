"""
Application Service - GerarFormulacaoInicialService.

Segunda etapa do fluxo de criação (seção 6, passos 3-4): usuário já
revisou/editou as exigências (via AtualizarExigenciaService) e agora
seleciona os ingredientes. Este service:

  1. Cria IngredienteFormulacao para cada ingrediente (ms_porcent=0, CALCULADA).
  2. Chama MotorAdequacao.gerar_distribuicao_inicial() (SciPy SLSQP).
  3. Aplica as frações resultantes.
  4. Dispara RecalcularFormulacaoService → snapshot v1.
  5. Promove a formulação para status ATIVA.

Pré-condição: a formulação já deve ter ExigenciaConfigurada
(criada por IniciarFormulacaoService). Caso contrário, levanta erro.

Só pode ser chamado uma vez por formulação em estado RASCUNHO —
chamadas subsequentes de adição/remoção de ingrediente usam
AdicionarIngredienteService / RemoverIngredienteService.
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
        if not ingrediente_ids:
            raise ValueError("Selecione ao menos um ingrediente.")

        formulacao = Formulacao.objects.get(pk=formulacao_id)

        if not ExigenciaConfigurada.objects.filter(formulacao_id=formulacao_id).exists():
            raise ValueError(
                f"Formulação {formulacao_id} não possui ExigenciaConfigurada. "
                "Chame IniciarFormulacaoService primeiro."
            )

        if IngredienteFormulacao.objects.filter(formulacao_id=formulacao_id).exists():
            raise ValueError(
                f"Formulação {formulacao_id} já possui ingredientes. "
                "Use AdicionarIngredienteService para incluir novos."
            )

        ingredientes = list(Ingrediente.objects.filter(pk__in=ingrediente_ids))
        if len(ingredientes) != len(ingrediente_ids):
            faltando = set(ingrediente_ids) - {i.pk for i in ingredientes}
            raise ValueError(f"Ingredientes não encontrados: {faltando}")

        ordem = {id_: pos for pos, id_ in enumerate(ingrediente_ids)}
        ingredientes.sort(key=lambda i: ordem[i.pk])

        # ------------------------------------------------------------------
        # Criar IngredienteFormulacao (ms_porcent=0, CALCULADA)
        # ------------------------------------------------------------------
        IngredienteFormulacao.objects.bulk_create([
            IngredienteFormulacao(
                formulacao=formulacao,
                ingrediente=ing,
                ms_porcent=0.0,
                origem_participacao=OrigemParticipacaoChoices.CALCULADA,
            )
            for ing in ingredientes
        ])

        # ------------------------------------------------------------------
        # Geração inicial via MotorAdequacao
        # ------------------------------------------------------------------
        vetores       = IngredienteFormulacaoRepository.get_vetores_nutricionais(formulacao_id)
        matriz_M      = MotorRecalculo.montar_matriz(vetores)
        requisitos    = ExigenciaRepository.get_requisitos(formulacao_id)
        configuracoes = [
            configuracao_a_partir_do_ingrediente(ing)
            for ing in ingredientes
        ]

        resultado_dist = MotorAdequacao.gerar_distribuicao_inicial(
            matriz_M=matriz_M,
            requisitos=requisitos,
            configuracoes=configuracoes,
            percentual_alvo_volumoso=percentual_alvo_volumoso,
        )

        # ------------------------------------------------------------------
        # Aplicar frações
        # ------------------------------------------------------------------
        qs_ing_form = list(
            IngredienteFormulacao.objects
            .filter(formulacao_id=formulacao_id)
            .order_by("id")
        )
        for pos, obj in enumerate(qs_ing_form):
            obj.ms_porcent = float(resultado_dist.fracoes[pos]) * 100.0

        IngredienteFormulacao.objects.bulk_update(qs_ing_form, fields=["ms_porcent"])

        # ------------------------------------------------------------------
        # Recálculo completo + snapshot v1
        # ------------------------------------------------------------------
        motivo = (
            "geração inicial"
            if resultado_dist.convergiu
            else f"geração inicial (fallback: {resultado_dist.mensagem})"
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
                "n_ingredientes":       len(ingredientes),
                "convergiu":            resultado_dist.convergiu,
                "mensagem_solver":      resultado_dist.mensagem,
                "percentual_alvo_vol":  percentual_alvo_volumoso,
            },
            usuario_id=usuario_id,
        )

        formulacao.status = StatusFormulacao.ATIVA
        formulacao.save(update_fields=["status"])

        return formulacao
