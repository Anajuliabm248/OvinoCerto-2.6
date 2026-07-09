"""
Application Service - RestaurarVersaoService.

Fase H do roadmap (seção 20).

Restaura o estado de participações (%MS) de uma formulação a partir
de um SnapshotFormulacao anterior, gerando uma nova versão — não
sobrescreve o histórico existente.

Estratégia
----------
1. Carrega o snapshot pelo versao_num.
2. Obtém a lista de participações do payload:
   [{id: <ing_form_id>, fracao: 0.30, origem: "CALCULADA"}, …]
3. Mapeia por ing_form_id os IngredienteFormulacao existentes.
4. Atualiza os que existem; ignora os que foram removidos.
5. Remove da formulação ativa os ingredientes que não constam no
   snapshot (foram adicionados depois).
6. Dispara RecalcularFormulacaoService → novo snapshot.

Cuidado com IGUAL / round-trip: a restauração não altera a
ExigenciaConfigurada, apenas as participações — sem risco de
double-tolerance em operadores IGUAL (conforme memória do projeto).
"""
from __future__ import annotations

from django.db import transaction

from formulacao.models import (
    Formulacao,
    IngredienteFormulacao,
    OrigemParticipacaoChoices,
    TipoEvento,
)
from formulacao.repositories import EventoRepository, SnapshotRepository
from formulacao.services.recalcular_formulacao_service import RecalcularFormulacaoService


class RestaurarVersaoService:

    @staticmethod
    @transaction.atomic
    def executar(
        formulacao_id: int,
        versao_num: int,
        usuario_id: int | None = None,
    ) -> Formulacao:
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

        # 2. Monta mapa {ing_form_id: (fracao, origem)}
        snap_map: dict[int, tuple[float, str]] = {
            int(p["id"]): (float(p["fracao"]), p.get("origem", "CALCULADA"))
            for p in participacoes_snap
        }
        snap_ids = set(snap_map.keys())

        # 3. Carrega IngredienteFormulacao atuais
        atuais = list(
            IngredienteFormulacao.objects.filter(formulacao_id=formulacao_id)
        )
        atuais_ids = {obj.pk for obj in atuais}

        # 4. Remove ingredientes que não constam no snapshot
        ids_remover = atuais_ids - snap_ids
        if ids_remover:
            IngredienteFormulacao.objects.filter(
                pk__in=ids_remover, formulacao_id=formulacao_id
            ).delete()

        # 5. Atualiza participações dos que existem no snapshot
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
        if ids_ausentes:
            # Não bloqueia — apenas registra no evento de auditoria.
            pass

        # 6. Recalcula → novo snapshot
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