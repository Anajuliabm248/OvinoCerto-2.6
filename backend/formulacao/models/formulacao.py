'''
Model da formulação da ração em si, definindo:
    - lote
    - usuario
    - titulo
    - satus 
    - datas
'''

from django.db import models

from accounts.models import Usuario
from lote.models import Lote

# pylint: disable= too-few-public-methods

class StatusFormulacao(models.TextChoices):
    '''Usado como escolha do status da formulacao'''
    RASCUNHO  = "RASCUNHO",  "Rascunho"
    ATIVA     = "ATIVA",     "Ativa"
    ARQUIVADA = "ARQUIVADA", "Arquivada"


class Formulacao(models.Model):
    """
    Raiz do agregado de formulação nutricional.

    Mantém apenas o que é essencial para identificação e ciclo de vida.
    Campos de custo/otimização econômica pertencem à fase futura e
    não existem aqui (ver documento de arquitetura, seção 1).

    Toda alteração nutricional relevante gera um SnapshotFormulacao
    vinculado — o estado "vivo" desta tabela e o último snapshot
    devem estar sempre sincronizados (seção 8).
    """

    lote = models.ForeignKey(
        Lote,
        on_delete=models.CASCADE,
        related_name="formulacoes",
        verbose_name="Lote",
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name="formulacoes",
        verbose_name="Usuário",
    )
    titulo = models.CharField(
        max_length=200,
        verbose_name="Título",
    )
    observacoes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observações",
    )
    status = models.CharField(
        max_length=10,
        choices=StatusFormulacao.choices,
        default=StatusFormulacao.RASCUNHO,
        verbose_name="Status",
        db_index=True,
    )
    percentual_alvo_volumoso = models.FloatField(
        default=0.50,
        verbose_name="Alvo de volumosos (fração da MS)",
        help_text=(
            "Participação total rígida de ingredientes classificados como "
            "volumoso, armazenada como fração de 0 a 1."
        ),
    )
    dt_inc = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    dt_alt = models.DateTimeField(auto_now=True,     verbose_name="Alterado em")

    
    # Indicadores de custo (Fase 2) — resumo, atualizado a cada recálculo.
    # Detalhe completo (breakdown por ingrediente) vive no payload do
    # SnapshotFormulacao, chave "custos". Estes campos existem soltos
    # aqui só para permitir listagem/ordenação rápida sem abrir o snapshot.
    

    custo_mn_kg = models.FloatField(null=True, blank=True, verbose_name="Custo (R$/kg MN)")
    custo_ms_kg = models.FloatField(null=True, blank=True, verbose_name="Custo (R$/kg MS)")
    custo_animal_dia = models.FloatField(null=True, blank=True, verbose_name="Custo (R$/animal/dia)")
    custo_lote_dia = models.FloatField(null=True, blank=True, verbose_name="Custo (R$/lote/dia)")

    class Meta:
        '''configs do BD'''
        verbose_name        = "Formulação"
        verbose_name_plural = "Formulações"
        ordering            = ["-dt_inc"]
        indexes = [
            models.Index(fields=["lote",    "-dt_inc"]),
            models.Index(fields=["usuario", "-dt_inc"]),
            models.Index(fields=["status",  "-dt_inc"]),
        ]

    def __str__(self):
        return f"{self.titulo} — {self.lote}"
