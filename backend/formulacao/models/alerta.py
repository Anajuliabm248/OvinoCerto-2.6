'''Model de alerta, ele emite um alerta no caso do nutriente
estar em excesso ou deficit e a porcentagem do desvio'''

from django.db import models

from formulacao.domain.nutrientes import Nutriente

from .formulacao import Formulacao
from .ingrediente_formulacao import IngredienteFormulacao

# pylint: disable= no-member, too-few-public-methods


NUTRIENTE_CHOICES = [(n.value, n.value) for n in Nutriente]


class TipoAlerta(models.TextChoices):
    '''servirá como escolha para o tipo de desvio'''
    DEFICIT = "DEFICIT", "Déficit"
    EXCESSO = "EXCESSO", "Excesso"
    SOMA    = "SOMA",    "Soma de participações fora de 100%"
    LIMITE_INGREDIENTE = "LIMITE_INGREDIENTE", "Limite de participação do ingrediente excedido"
    CUSTO_INDISPONIVEL = "CUSTO_INDISPONIVEL", "Preço não informado para ao menos um ingrediente"


class SeveridadeAlerta(models.TextChoices):
    '''servirá como escolha para o grau de atenção do desvio'''
    INFO     = "INFO",     "Informação (desvio ≤ 5%)"
    ATENCAO  = "ATENCAO",  "Atenção (desvio 5–20%)"
    CRITICO  = "CRITICO",  "Crítico (desvio > 20%)"


class Alerta(models.Model):
    """
    Alerta nutricional com ciclo de vida (gerado → resolvido).

    Gerado pelo MotorAlertas ao final de cada pipeline do MotorRecalculo.
    Nunca bloqueia a formulação — apenas informa (seção 12 e 15 do
    documento de arquitetura).

    Rastreabilidade:
    - snapshot_versao_geracao: em qual versão o alerta apareceu.
    - snapshot_versao_resolucao: em qual versão foi resolvido (None se ainda ativo).
    - resolvido=True preserva o registro histórico; o alerta não é deletado.

    Unicidade por (formulacao, nutriente, tipo): garante que não existam
    dois alertas ativos do mesmo tipo para o mesmo nutriente.
    Ao recalcular, alertas não repetidos são marcados resolvido=True;
    novos são inseridos.

    Alertas do tipo LIMITE_INGREDIENTE não são identificados por
    nutriente, e sim por `ingrediente_formulacao` (a unicidade nesse
    caso é (formulacao, tipo, ingrediente_formulacao)). São gerados
    quando a participação (%MS) de um ingrediente ultrapassa o
    `limite_max_participacao` configurado no seu cadastro — nunca
    bloqueiam a formulação, apenas sinalizam (mesma filosofia dos
    alertas nutricionais).
    """

    formulacao = models.ForeignKey(
        Formulacao,
        on_delete=models.CASCADE,
        related_name="alertas",
        verbose_name="Formulação",
    )
    nutriente = models.CharField(
        max_length=10,
        choices=NUTRIENTE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Nutriente",
        help_text="Null para alertas de tipo SOMA ou LIMITE_INGREDIENTE (não associados a nutriente específico).",
        db_index=True,
    )
    tipo = models.CharField(
        max_length=25,
        choices=TipoAlerta.choices,
        verbose_name="Tipo",
    )
    ingrediente_formulacao = models.ForeignKey(
        IngredienteFormulacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alertas_limite",
        verbose_name="Ingrediente na formulação",
        help_text=(
            "Preenchido apenas para alertas do tipo LIMITE_INGREDIENTE: "
            "identifica qual ingrediente ultrapassou o limite de participação."
        ),
        db_index=True,
    )
    ingrediente_nome = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="Nome do ingrediente (histórico)",
        help_text=(
            "Cópia do nome do ingrediente no momento da geração do alerta — "
            "preserva a informação mesmo se o ingrediente for removido da formulação."
        ),
    )
    severidade = models.CharField(
        max_length=10,
        choices=SeveridadeAlerta.choices,
        verbose_name="Severidade",
        db_index=True,
    )
    valor_atual = models.FloatField(
        verbose_name="Valor atual (% MS)",
    )
    valor_limite = models.FloatField(
        verbose_name="Valor limite violado (% MS)",
        help_text="O limite (min ou max) que foi ultrapassado.",
    )
    magnitude_relativa = models.FloatField(
        default=0.0,
        verbose_name="Magnitude relativa",
        help_text="Proporção do desvio em relação ao limite (ex.: 0.20 = 20% fora do limite).",
    )

    # Rastreabilidade de versão
    snapshot_versao_geracao = models.PositiveIntegerField(
        verbose_name="Versão em que foi gerado",
    )
    snapshot_versao_resolucao = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Versão em que foi resolvido",
    )

    resolvido = models.BooleanField(
        default=False,
        verbose_name="Resolvido",
        db_index=True,
    )
    dt_geracao  = models.DateTimeField(auto_now_add=True, verbose_name="Gerado em")
    dt_resolucao = models.DateTimeField(null=True, blank=True, verbose_name="Resolvido em")

    class Meta:
        '''configs do banco de dados'''
        verbose_name        = "Alerta Nutricional"
        verbose_name_plural = "Alertas Nutricionais"
        ordering            = ["-dt_geracao", "severidade"]
        indexes = [
            models.Index(fields=["formulacao", "resolvido"]),
            models.Index(fields=["formulacao", "nutriente", "tipo"]),
            models.Index(fields=["formulacao", "severidade", "resolvido"]),
            models.Index(fields=["formulacao", "tipo", "ingrediente_formulacao"]),
        ]

    def __str__(self):
        if self.tipo == TipoAlerta.LIMITE_INGREDIENTE:
            referencia = self.ingrediente_nome or "(ingrediente removido)"
        else:
            referencia = self.nutriente or "SOMA"
        status = "✓" if self.resolvido else "!"
        return f"[{status}] {self.severidade} — {referencia} {self.tipo} (formulação {self.formulacao_id})"
