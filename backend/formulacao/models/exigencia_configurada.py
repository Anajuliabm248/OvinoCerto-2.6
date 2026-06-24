'''Model para que o usuario possa configurar a exigencia 
da sua própria formulação'''

from django.db import models

from accounts.models import Usuario
from exigencia_nrc.models import ExigenciaNRC
from formulacao.domain.nutrientes import Nutriente
from formulacao.domain.requisito import Operador

from .formulacao import Formulacao

# pylint: disable= too-few-public-methods, no-member

# Choices derivadas dos enums do domínio puro
# (mantemos choices Django separadas dos enums de domínio para não
# criar dependência de Django dentro da camada de domínio)

NUTRIENTE_CHOICES = [(n.value, n.value) for n in Nutriente]

OPERADOR_CHOICES = [
    (Operador.IGUAL.value,       "Igual (=)"),
    (Operador.MAIOR_IGUAL.value, "Maior ou igual (>=)"),
    (Operador.MENOR_IGUAL.value, "Menor ou igual (<=)"),
    (Operador.ENTRE.value,       "Entre (intervalo)"),
]


class ExigenciaConfigurada(models.Model):
    """
    Cópia editável das exigências NRC para UMA formulação específica.
 
    Criada automaticamente a partir de ExigenciaNRC.lookup() no momento
    da criação da formulação, com alterado_pelo_usuario=False em todos
    os ConfiguracaoNutriente filhos.
 
    Alterar esta entidade nunca afeta a tabela ExigenciaNRC original —
    ela é apenas a referência de origem (seção 15 do documento de
    arquitetura).
    """

    formulacao = models.OneToOneField(
        Formulacao,
        on_delete=models.CASCADE,
        related_name="exigencia_configurada",
        verbose_name="Formulação",
    )
    exigencia_nrc_origem = models.ForeignKey(
        ExigenciaNRC,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exigencias_configuradas",
        verbose_name="Exigência NRC de origem",
        help_text="Referência read-only à linha NRC usada como ponto de partida.",
    )
    cms_kg = models.FloatField(
        verbose_name="CMS (kg/dia)",
        help_text="Consumo de Matéria Seca do lote, calculado no momento da criação.",
    )

    class Meta:
        '''configs do banco de dados'''
        verbose_name        = "Exigência Configurada"
        verbose_name_plural = "Exigências Configuradas"

    def __str__(self):
        return f"Exigência de {self.formulacao}"


class ConfiguracaoNutriente(models.Model):
    """
    Configuração de UM nutriente dentro de uma ExigenciaConfigurada.

    Cada linha representa o operador e os limites que o MotorRecalculo
    vai usar para comparar o valor calculado da formulação.

    valor_min / valor_max em % da MS (mesma unidade de VetorNutricional).
    Ambos nullable: ">=" só tem valor_min; "<=" só tem valor_max.

    Invariante: para operador ENTRE, valor_min < valor_max (validado
    no Application Service antes de persistir).
    """

    exigencia_configurada = models.ForeignKey(
        ExigenciaConfigurada,
        on_delete=models.CASCADE,
        related_name="configuracoes_nutrientes",
        verbose_name="Exigência configurada",
    )
    nutriente = models.CharField(
        max_length=10,
        choices=NUTRIENTE_CHOICES,
        verbose_name="Nutriente",
        db_index=True,
    )
    operador = models.CharField(
        max_length=10,
        choices=OPERADOR_CHOICES,
        verbose_name="Operador",
    )
    valor_min = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Valor mínimo (% MS)",
    )
    valor_max = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Valor máximo (% MS)",
    )
    valor_origem_nrc = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Valor original NRC (% MS)",
        help_text="Valor percentual que veio da tabela NRC; preservado para rastreabilidade.",
    )
    alterado_pelo_usuario = models.BooleanField(
        default=False,
        verbose_name="Alterado pelo usuário",
    )
    dt_alteracao = models.DateTimeField(
        auto_now=True,
        verbose_name="Última alteração",
    )

    class Meta:
        '''configs do banco de dados'''
        verbose_name        = "Configuração de Nutriente"
        verbose_name_plural = "Configurações de Nutrientes"
        unique_together     = [("exigencia_configurada", "nutriente")]
        ordering            = ["nutriente"]

    def __str__(self):
        return f"{self.nutriente} {self.operador} \
                    (formulação {self.exigencia_configurada.formulacao_id})"


class HistoricoConfiguracaoNutriente(models.Model):
    """
    Log append-only de cada alteração em ConfiguracaoNutriente.

    Registra intenção (o que o usuário mudou) separadamente de efeito
    (SnapshotFormulacao registra o estado resultante).
    Nunca é editado — apenas inserido (seção 8 do documento de arquitetura).
    """

    configuracao = models.ForeignKey(
        ConfiguracaoNutriente,
        on_delete=models.CASCADE,
        related_name="historico",
        verbose_name="Configuração",
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name="historico_configuracoes",
        verbose_name="Usuário",
    )
    # Estado anterior
    operador_anterior  = models.CharField(max_length=10, choices=OPERADOR_CHOICES)
    valor_min_anterior = models.FloatField(null=True, blank=True)
    valor_max_anterior = models.FloatField(null=True, blank=True)
    # Estado novo
    operador_novo      = models.CharField(max_length=10, choices=OPERADOR_CHOICES)
    valor_min_novo     = models.FloatField(null=True, blank=True)
    valor_max_novo     = models.FloatField(null=True, blank=True)

    dt_alteracao = models.DateTimeField(auto_now_add=True, verbose_name="Data da alteração")

    class Meta:
        '''configs do banco de dados'''
        verbose_name        = "Histórico de Configuração de Nutriente"
        verbose_name_plural = "Históricos de Configurações de Nutrientes"
        ordering            = ["-dt_alteracao"]

    def __str__(self):
        return (
            f"{self.configuracao.nutriente}: "
            f"{self.operador_anterior} → {self.operador_novo} "
            f"({self.dt_alteracao:%Y-%m-%d %H:%M})"
        )
