"""
Repository - SnapshotFormulacao / EventoFormulacao.

Controla o incremento de versao_num por formulacao_id e persiste
o estado completo serializado (payload jsonb).

versao_num é garantido por select_for_update() na linha de
SnapshotFormulacao mais recente, evitando race conditions em
concorrência (seção 8 do documento de arquitetura).
"""

from __future__ import annotations

from django.db import transaction

from formulacao.models import EventoFormulacao, SnapshotFormulacao, TipoEvento


class SnapshotRepository:
    """Versiona de forma sequencial o estado completo de cada formulação."""
    

    @staticmethod
    @transaction.atomic
    def criar(
        formulacao_id: int,
        payload: dict,
        motivo: str = "",
        usuario_id: int | None = None,
    ) -> SnapshotFormulacao:
        """
        Cria um novo snapshot com versao_num = último + 1.

        O select_for_update() no último snapshot garante que duas
        requisições simultâneas não gerem o mesmo versao_num.
        """
        ultimo = (
            SnapshotFormulacao.objects
            .select_for_update()
            .filter(formulacao_id=formulacao_id)
            .order_by("-versao_num")
            .first()
        )
        proximo_num = (ultimo.versao_num + 1) if ultimo else 1

        return SnapshotFormulacao.objects.create(
            formulacao_id=formulacao_id,
            versao_num=proximo_num,
            payload=payload,
            motivo=motivo,
            usuario_id=usuario_id,
        )

    
    # Leitura
    

    @staticmethod
    def get_ultimo(formulacao_id: int) -> SnapshotFormulacao | None:
        """Retorna a versão mais recente ou ``None`` quando ainda não há histórico."""
        return (
            SnapshotFormulacao.objects
            .filter(formulacao_id=formulacao_id)
            .order_by("-versao_num")
            .first()
        )

    @staticmethod
    def get_versao(formulacao_id: int, versao_num: int) -> SnapshotFormulacao:
        """Levanta SnapshotFormulacao.DoesNotExist se não encontrado."""
        return SnapshotFormulacao.objects.get(
            formulacao_id=formulacao_id,
            versao_num=versao_num,
        )

    @staticmethod
    def listar(formulacao_id: int):
        """
        Retorna QuerySet ordenado do mais recente para o mais antigo.
        Não inclui `payload` (campo pesado) — apenas metadados para
        listagem (seção 17: payload só lido sob demanda).
        """
        return (
            SnapshotFormulacao.objects
            .filter(formulacao_id=formulacao_id)
            .order_by("-versao_num")
            .defer("payload")
        )

    @staticmethod
    def get_versao_atual(formulacao_id: int) -> int:
        """Retorna o versao_num mais alto, ou 0 se não houver snapshots."""
        ultimo = (
            SnapshotFormulacao.objects
            .filter(formulacao_id=formulacao_id)
            .order_by("-versao_num")
            .values_list("versao_num", flat=True)
            .first()
        )
        return ultimo or 0


class EventoRepository:
    """Persiste e consulta a trilha imutável de ações feitas na formulação."""

    @staticmethod
    def registrar(
        formulacao_id: int,
        tipo_evento: TipoEvento,
        payload: dict | None = None,
        usuario_id: int | None = None,
    ) -> EventoFormulacao:
        """Registra tipo, contexto e autoria de uma mudança feita na formulação."""
        return EventoFormulacao.objects.create(
            formulacao_id=formulacao_id,
            tipo_evento=tipo_evento,
            payload=payload or {},
            usuario_id=usuario_id,
        )

    @staticmethod
    def listar(formulacao_id: int):
        """Lista os eventos da formulação começando pelo mais recente."""
        return (
            EventoFormulacao.objects
            .filter(formulacao_id=formulacao_id)
            .order_by("-dt_criacao")
        )
