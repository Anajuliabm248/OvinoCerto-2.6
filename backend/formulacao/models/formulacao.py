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


class ModoPercentualVolumoso(models.TextChoices):
    """Define se o total de volumoso e restricao ou resultado do motor."""

    FIXADO_PELO_USUARIO = "FIXADO_PELO_USUARIO", "Fixado pelo usuario"
    OTIMIZADO_PELO_SISTEMA = "OTIMIZADO_PELO_SISTEMA", "Otimizado pelo sistema"


class OrigemPercentualVolumoso(models.TextChoices):
    """Origem auditavel do percentual efetivamente aplicado."""

    USUARIO = "USUARIO", "Usuario"
    SISTEMA = "SISTEMA", "Sistema"


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
        null=True,
        blank=True,
        verbose_name="Alvo de volumosos (fração da MS)",
        help_text=(
            "Fonte de verdade do alvo rigido somente quando o modo e "
            "FIXADO_PELO_USUARIO. Armazenado como fracao de 0 a 1; fica "
            "nulo no modo OTIMIZADO_PELO_SISTEMA."
        ),
    )
    modo_percentual_volumoso = models.CharField(
        max_length=30,
        choices=ModoPercentualVolumoso.choices,
        default=ModoPercentualVolumoso.FIXADO_PELO_USUARIO,
        verbose_name="Modo de definição do volumoso",
        help_text=(
            "Controla o motor: no modo fixado, percentual_alvo_volumoso e "
            "restricao rigida; no automatico, o total de volumoso e resultado."
        ),
    )
    percentual_volumoso_aplicado = models.FloatField(
        default=0.50,
        verbose_name="Volumoso efetivamente aplicado (fração da MS)",
        help_text=(
            "Resultado auditavel entre 0 e 1, calculado a partir das "
            "participacoes persistidas; nunca configura o motor."
        ),
    )
    origem_percentual_volumoso = models.CharField(
        max_length=10,
        choices=OrigemPercentualVolumoso.choices,
        default=OrigemPercentualVolumoso.USUARIO,
        verbose_name="Origem do percentual de volumoso",
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
    quantidade_mistura_mn_kg = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Quantidade da mistura concentrada (kg MN)",
        help_text=(
            "Quantidade persistida de matéria natural da mistura concentrada "
            "a preparar. Deve ser maior que zero quando informada."
        ),
    )

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
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        modo_percentual_volumoso=ModoPercentualVolumoso.FIXADO_PELO_USUARIO,
                        percentual_alvo_volumoso__isnull=False,
                        origem_percentual_volumoso=OrigemPercentualVolumoso.USUARIO,
                    )
                    | models.Q(
                        modo_percentual_volumoso=ModoPercentualVolumoso.OTIMIZADO_PELO_SISTEMA,
                        percentual_alvo_volumoso__isnull=True,
                        origem_percentual_volumoso=OrigemPercentualVolumoso.SISTEMA,
                    )
                ),
                name="formulacao_estado_volumoso_coerente",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(percentual_alvo_volumoso__isnull=True)
                    | models.Q(
                        percentual_alvo_volumoso__gte=0.0,
                        percentual_alvo_volumoso__lte=1.0,
                    )
                ),
                name="formulacao_alvo_volumoso_0_1",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    percentual_volumoso_aplicado__gte=0.0,
                    percentual_volumoso_aplicado__lte=1.0,
                ),
                name="formulacao_aplicado_volumoso_0_1",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(quantidade_mistura_mn_kg__isnull=True)
                    | models.Q(quantidade_mistura_mn_kg__gt=0.0)
                ),
                name="formulacao_quantidade_mistura_mn_positiva",
            ),
        ]

    def __str__(self):
        return f"{self.titulo} — {self.lote}"

    @property
    def percentual_volumoso_para_motor(self) -> float | None:
        """Retorna alvo somente quando a configuracao realmente o fixa."""
        if self.modo_percentual_volumoso == ModoPercentualVolumoso.FIXADO_PELO_USUARIO:
            if self.percentual_alvo_volumoso is None:
                raise ValueError(
                    "Formulação em modo fixado sem percentual alvo configurado."
                )
            return self.percentual_alvo_volumoso
        return None
