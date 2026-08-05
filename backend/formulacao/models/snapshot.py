'''snapshot da formualação, usado para controle de versionamento e segurança'''

from django.db import models

from accounts.models import Usuario

from .formulacao import Formulacao

# pylint: disable= no-member, too-few-public-methods

class SnapshotFormulacao(models.Model):
    """
    Snapshot append-only do estado completo de uma formulação.

    Nunca é editado após criação. Cada alteração nutricional relevante
    (geração inicial, edição manual, redistribuição, mudança de
    exigência configurada) gera um novo registro com versao_num
    incrementado (seção 13 do documento de arquitetura).

    payload: jsonb auto-contido — contém participações, resultado de
    adequação, alertas, exigência configurada vigente, schema_version.
    Suficiente para reconstruir o estado sem depender do estado atual
    de outras tabelas (exceto referências read-only a Ingrediente por id).

    schema_version dentro do payload permite evolução do formato sem
    quebrar snapshots antigos (seção 16).
    """

    formulacao = models.ForeignKey(
        Formulacao,
        on_delete=models.CASCADE,
        related_name="snapshots",
        verbose_name="Formulação",
    )
    versao_num = models.PositiveIntegerField(
        verbose_name="Número da versão",
        help_text="Incrementado por formulacao_id. Unicidade garantida por unique_together.",
    )
    payload = models.JSONField(
        verbose_name="Payload (estado completo)",
        help_text=(
            "JSON auto-contido com: participacoes, resultado_adequacao, "
            "alertas, exigencia_configurada, schema_version, dt_criacao, usuario_id, motivo."
        ),
    )
    motivo = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Motivo da versão",
        help_text="Ex.: 'geração inicial', 'edição manual ms_porcent', 'adição de ingrediente'.",
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="snapshots_formulacao",
        verbose_name="Usuário",
    )
    dt_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em",
    )

    class Meta:
        '''configs do BD'''
        verbose_name        = "Snapshot de Formulação"
        verbose_name_plural = "Snapshots de Formulação"
        ordering            = ["formulacao", "versao_num"]
        unique_together     = [("formulacao", "versao_num")]
        indexes = [
            models.Index(fields=["formulacao", "-versao_num"]),
        ]

    def __str__(self):
        return f"Formulação {self.formulacao_id} v{self.versao_num} ({self.motivo or 'sem motivo'})"


class TipoEvento(models.TextChoices):
    '''escolhas do tipo de versionamento'''
    CRIACAO                  = "CRIACAO",                  "Formulação criada"
    INGREDIENTE_ADICIONADO   = "INGREDIENTE_ADICIONADO",   "Ingrediente adicionado"
    INGREDIENTE_REMOVIDO     = "INGREDIENTE_REMOVIDO",     "Ingrediente removido"
    PARTICIPACAO_EDITADA     = "PARTICIPACAO_EDITADA",     "Participação editada manualmente"
    PARTICIPACAO_DESTRAVADA  = "PARTICIPACAO_DESTRAVADA",  "Participação destravada"
    EXIGENCIA_ALTERADA       = "EXIGENCIA_ALTERADA",       "Exigência configurada alterada"
    RECALCULO_SOLICITADO     = "RECALCULO_SOLICITADO",     "Recálculo explícito solicitado"
    REDISTRIBUICAO_EXECUTADA = "REDISTRIBUICAO_EXECUTADA", "Redistribuição automática executada"
    VERSAO_RESTAURADA        = "VERSAO_RESTAURADA",        "Estado restaurado a partir de snapshot"
    PRECO_ATUALIZADO         = "PRECO_ATUALIZADO",         "Preço de ingrediente atualizado"


class EventoFormulacao(models.Model):
    """
    Log de eventos de negócio da formulação.

    Complementa SnapshotFormulacao: registra a *intenção* (o que o
    usuário ou o sistema fez) separadamente do *efeito* (estado
    resultante, que vai no snapshot).

    Útil para responder "o que aconteceu entre as versões 3 e 4?"
    sem precisar comparar payloads de dois snapshots.

    Nunca editado após criação (append-only).
    """

    formulacao = models.ForeignKey(
        Formulacao,
        on_delete=models.CASCADE,
        related_name="eventos",
        verbose_name="Formulação",
    )
    tipo_evento = models.CharField(
        max_length=30,
        choices=TipoEvento.choices,
        verbose_name="Tipo de evento",
        db_index=True,
    )
    payload = models.JSONField(
        default=dict,
        verbose_name="Dados do evento",
        help_text="Contexto específico do evento \
        (ex.: {ingrediente_id: 42, ms_porcent_anterior: 30.0}).",
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_formulacao",
        verbose_name="Usuário",
    )
    dt_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        '''config do BD'''
        verbose_name        = "Evento de Formulação"
        verbose_name_plural = "Eventos de Formulação"
        ordering            = ["formulacao", "dt_criacao"]
        indexes = [
            models.Index(fields=["formulacao", "-dt_criacao"]),
            models.Index(fields=["formulacao", "tipo_evento"]),
        ]

    def __str__(self):
        return f"{self.get_tipo_evento_display()}\
                — formulação {self.formulacao_id} ({self.dt_criacao:%d-%m-%y %H:%M})"
