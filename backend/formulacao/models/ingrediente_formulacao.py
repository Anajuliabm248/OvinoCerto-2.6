'''Model para conectar o ingrediente à formulação'''

from django.db import models

from ingrediente.models import Ingrediente

from .formulacao import Formulacao

# pylint: disable= too-few-public-methods, no-member

class OrigemParticipacaoChoices(models.TextChoices):
    """
    Espelha o enum OrigemParticipacao do domínio puro
    (formulacao/domain/participacao.py) — não importamos o enum de
    domínio diretamente aqui para não criar dependência Django → domínio
    nos models; o repositório faz a tradução entre os dois.
    """
    CALCULADA      = "CALCULADA",      "Calculada pelo sistema"
    MANUAL_TRAVADA = "MANUAL_TRAVADA", "Travada pelo usuário"


class OrigemCustoChoices(models.TextChoices):
    """Distingue preço regional do usuário e preço particular da receita."""
    CATALOGO       = "CATALOGO",       "Banco de preços do usuário"
    OVERRIDE_LOCAL = "OVERRIDE_LOCAL", "Sobrescrito nesta formulação"


class IngredienteFormulacao(models.Model):
    """
    Participação de UM ingrediente em UMA formulação.

    ms_porcent: armazenado em percentual (0-100) no banco para
    legibilidade. O repositório converte para fração (0-1) ao
    construir ParticipacaoVetor para o domínio, e converte de volta
    ao persistir a saída do MotorRecalculo.

    Os campos *_kg são calculados pelo MotorRecalculo e persistidos
    pelo repositório após cada recálculo — nunca editados diretamente.
    mn_kg é calculado a partir de ms_kg / (ms% / 100).

    Campos de custo (custo_kg_mn_override, origem_custo, custo_dia)
    pertencem à Fase 2 — ver docstring de OrigemCustoChoices e
    formulacao/engines/motor_custo.py.
    """

    formulacao = models.ForeignKey(
        Formulacao,
        on_delete=models.CASCADE,
        related_name="ingredientes_formulacao",
        verbose_name="Formulação",
    )
    ingrediente = models.ForeignKey(
        Ingrediente,
        on_delete=models.SET_NULL,
        null=True,
        related_name="ingredientes_formulacao",
        verbose_name="Ingrediente",
        help_text=(
            "SET_NULL preserva o registro mesmo se o ingrediente for excluído; "
            "o SnapshotFormulacao guarda o vetor nutricional capturado no momento."
        ),
    )

    
    # Participação
    
    ms_porcent = models.FloatField(
        default=0.0,
        verbose_name="Participação % MS",
        help_text="Percentual da MS total (0-100). \
        O repositório converte para fração 0-1 no domínio.",
    )
    origem_participacao = models.CharField(
        max_length=15,
        choices=OrigemParticipacaoChoices.choices,
        default=OrigemParticipacaoChoices.CALCULADA,
        verbose_name="Origem da participação",
        db_index=True,
        help_text=(
            "CALCULADA = definida/ajustada pelo sistema. "
            "MANUAL_TRAVADA = editada pelo usuário; nunca alterada por redistribuição automática."
        ),
    )

    
    # Quantidades calculadas (preenchidas pelo MotorRecalculo via repositório)
    
    ms_kg  = models.FloatField(default=0.0, verbose_name="MS (kg/animal/dia)")
    mn_kg  = models.FloatField(default=0.0, verbose_name="MN (kg/animal/dia)")
    pb_kg  = models.FloatField(default=0.0, verbose_name="PB (kg/dia)")
    ndt_kg = models.FloatField(default=0.0, verbose_name="NDT (kg/dia)")
    fdn_kg = models.FloatField(default=0.0, verbose_name="FDN (kg/dia)")
    ee_kg  = models.FloatField(default=0.0, verbose_name="EE (kg/dia)")
    ca_kg  = models.FloatField(default=0.0, verbose_name="Ca (kg/dia)")
    p_kg   = models.FloatField(default=0.0, verbose_name="P (kg/dia)")

    
    # Custo (Fase 2)
    

    custo_kg_mn_override = models.FloatField(
        null=True, blank=True,
        verbose_name="Custo local (R$/kg MN)",
        help_text=(
            "Preenchido quando o usuário escolhe 'atualizar preço só "
            "nesta receita'. Null = usa o banco de preços regional do "
            "usuário (PrecoIngredienteUsuario)."
        ),
    )
    origem_custo = models.CharField(
        max_length=17,
        choices=OrigemCustoChoices.choices,
        default=OrigemCustoChoices.CATALOGO,
        verbose_name="Origem do custo",
    )
    custo_dia = models.FloatField(
        default=0.0,
        verbose_name="Custo (R$/animal/dia)",
        help_text="Calculado pelo MotorCusto via repositório — nunca editado diretamente.",
    )

    class Meta:
        '''configurações básicas do banco de dados'''
        verbose_name        = "Ingrediente na Formulação"
        verbose_name_plural = "Ingredientes na Formulação"
        ordering            = ["-ms_porcent"]
        unique_together     = [("formulacao", "ingrediente")]
        indexes = [
            models.Index(fields=["formulacao", "origem_participacao"]),
        ]

    def __str__(self):
        nome = self.ingrediente.nome if self.ingrediente else "(removido)"
        return f"{nome} — {self.ms_porcent:.1f}% MS [{self.origem_participacao}]"
