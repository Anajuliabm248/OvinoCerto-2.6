"""
Application Service - RestaurarVersaoService.

Fase H do roadmap (seção 20).

Restaura o estado de participações (%MS) e exigências configuradas de
uma formulação a partir de um SnapshotFormulacao anterior, gerando uma
nova versão — não sobrescreve o histórico existente.

Estratégia
----------
1. Carrega o snapshot pelo versao_num.
2. Restaura a exigência configurada gravada no payload.
3. Obtém a lista de participações do payload:
   [{id: <ing_form_id>, fracao: 0.30, origem: "CALCULADA"}, …]
4. Mapeia por ing_form_id os IngredienteFormulacao existentes.
5. Atualiza os que existem; ignora os que foram removidos.
6. Remove da formulação ativa os ingredientes que não constam no
   snapshot (foram adicionados depois).
7. Dispara RecalcularFormulacaoService → novo snapshot.

Os valores dos operadores são restaurados como foram serializados. A
tolerância do operador IGUAL continua sendo aplicada somente quando o
requisito é reconstruído pela camada de domínio.
"""
from __future__ import annotations

from django.db import transaction

from formulacao.models import (
    Formulacao,
    IngredienteFormulacao,
    OrigemParticipacaoChoices,
    TipoEvento,
)
from formulacao.repositories import (
    EventoRepository,
    ExigenciaRepository,
    SnapshotRepository,
)
from formulacao.services.recalcular_formulacao_service import RecalcularFormulacaoService


class RestaurarVersaoService:
    """Recupera uma versão antiga e cria outra versão auditável com esse estado."""

    @staticmethod
    @transaction.atomic
    def executar(
        formulacao_id: int,
        versao_num: int,
        usuario_id: int | None = None,
    ) -> Formulacao:
        """Aplica participações antigas, recalcula e registra uma nova versão."""
        # 1. Carrega snapshot
        from formulacao.models import SnapshotFormulacao
        try:
            snapshot = SnapshotRepository.get_versao(formulacao_id, versao_num)
        except SnapshotFormulacao.DoesNotExist:
            raise ValueError(
                f"Versão {versao_num} não encontrada na formulação {formulacao_id}."
            )

        participacoes_snap: list[dict] = snapshot.payload.get("participacoes", [])
        if not participacoes_snap:
            raise ValueError(
                f"Snapshot versão {versao_num} não contém dados de participação."
            )

        # 2. Restaura a exigência que estava vigente naquela versão antes
        # de recalcular. O recálculo subsequente registra um novo snapshot
        # coerente, com participações e exigências da mesma versão histórica.
        ExigenciaRepository.restaurar_configuracao(
            formulacao_id=formulacao_id,
            configuracao_snapshot=snapshot.payload.get("exigencia_configurada"),
        )
        percentual_alvo_volumoso = snapshot.payload.get("percentual_alvo_volumoso")
        if percentual_alvo_volumoso is not None:
            try:
                percentual_alvo_volumoso = float(percentual_alvo_volumoso)
            except (TypeError, ValueError):
                raise ValueError(
                    "A versão selecionada contém percentual de volumoso inválido."
                ) from None
            if not 0.0 <= percentual_alvo_volumoso <= 1.0:
                raise ValueError(
                    "A versão selecionada contém percentual de volumoso inválido."
                )
            Formulacao.objects.filter(pk=formulacao_id).update(
                percentual_alvo_volumoso=percentual_alvo_volumoso
            )

        # 3. Monta mapa {ing_form_id: (fracao, origem)}
        snap_map: dict[int, tuple[float, str]] = {
            int(p["id"]): (float(p["fracao"]), p.get("origem", "CALCULADA"))
            for p in participacoes_snap
        }
        snap_ids = set(snap_map.keys())

        # 4. Carrega IngredienteFormulacao atuais
        atuais = list(
            IngredienteFormulacao.objects.filter(formulacao_id=formulacao_id)
        )
        atuais_ids = {obj.pk for obj in atuais}

        # 5. Remove ingredientes que não constam no snapshot
        ids_remover = atuais_ids - snap_ids
        if ids_remover:
            IngredienteFormulacao.objects.filter(
                pk__in=ids_remover, formulacao_id=formulacao_id
            ).delete()

        # 6. Atualiza participações dos que existem no snapshot
        para_update: list[IngredienteFormulacao] = []
        for obj in atuais:
            if obj.pk in snap_map:
                fracao, origem = snap_map[obj.pk]
                obj.ms_porcent = fracao * 100.0
                obj.origem_participacao = _mapear_origem(origem)
                para_update.append(obj)

        if para_update:
            IngredienteFormulacao.objects.bulk_update(
                para_update, fields=["ms_porcent", "origem_participacao"]
            )

        # IDs presentes no snapshot mas removidos da formulação (sem restauração possível)
        ids_ausentes = snap_ids - atuais_ids

        # 7. Recalcula → novo snapshot
        motivo = f"restauração da versão {versao_num}"
        RecalcularFormulacaoService.executar(
            formulacao_id=formulacao_id,
            usuario_id=usuario_id,
            motivo=motivo,
        )

        EventoRepository.registrar(
            formulacao_id=formulacao_id,
            tipo_evento=TipoEvento.VERSAO_RESTAURADA,
            payload={
                "acao": "restaurar_versao",
                "versao_restaurada": versao_num,
                "exigencias_restauradas": True,
                "percentual_alvo_volumoso_restaurado": percentual_alvo_volumoso,
                "ids_ausentes": list(ids_ausentes),
                "ids_removidos": list(ids_remover),
            },
            usuario_id=usuario_id,
        )

        return Formulacao.objects.get(pk=formulacao_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mapear_origem(origem_str: str) -> str:
    """Converte string do payload para OrigemParticipacaoChoices."""
    mapa = {
        "CALCULADA":      OrigemParticipacaoChoices.CALCULADA,
        "MANUAL_TRAVADA": OrigemParticipacaoChoices.MANUAL_TRAVADA,
    }
    return mapa.get(origem_str, OrigemParticipacaoChoices.CALCULADA)
