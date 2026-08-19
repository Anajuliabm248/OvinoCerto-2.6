"""Catálogo nutricional e preços particulares de ingredientes.

Ingredientes Valadares são compartilhados e somente leitura. Ingredientes
customizados pertencem a um usuário. Preços ficam em uma tabela separada para
que cada produtor possa manter valores regionais sem alterar o catálogo comum.
"""

from django.db import models
from accounts.models import Usuario

# pylint: disable= no-member, too-few-public-methods

CLASSIFICACAO_CHOICES = [
    ('volumoso',    'Volumoso'),
    ('concentrado', 'Concentrado'),
]

TIPO_CHOICES = [
    # Volumosos
    ('forragens_secas',   'Forragens Secas'),
    ('forragens_verdes',  'Forragens Verdes'),
    ('silagens',          'Silagens'),
    # Concentrados
    ('energetico',        'Energético'),
    ('proteico',          'Proteico'),
    ('mineral',           'Mineral'),
    ('aditivos',          'Aditivos'),
    # Outros
    ('outro',             'Outro'),
]
TIPO_EXCEL_MAP = {
    'Forragens Secas':  'forragens_secas',
    'Forragens Verdes': 'forragens_verdes',
    'Silagens':         'silagens',
    'Energético':       'energetico',
    'Proteico':         'proteico',
    'Mineral':          'mineral',
    'Aditivos':         'aditivos',
}


class Ingrediente(models.Model):
    """
    Ingrediente para formulação de dietas ovinas.

    ``fonte_valadares=True`` identifica linhas públicas importadas da tabela.
    As demais linhas são customizadas e devem ter um usuário proprietário.
    """

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='ingredientes_custom',
        blank=True, null=True,
        verbose_name='Usuário (custom)',
    )

    classificacao = models.CharField(
        max_length=20,
        choices=CLASSIFICACAO_CHOICES,
        verbose_name='Classificação',
        db_index=True,
    )
    tipo = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES,
        verbose_name='Tipo',
        db_index=True,
    )
    nome = models.CharField(
        max_length=200,
        verbose_name='Nome do ingrediente',
    )

    # Composição bromatológica (base matéria seca, %)
    ms  = models.FloatField(verbose_name='MS (%)')
    pb  = models.FloatField(verbose_name='PB (%)')
    ndt = models.FloatField(verbose_name='NDT (%)')
    fdn = models.FloatField(verbose_name='FDN (%)')
    ee  = models.FloatField(verbose_name='EE (%)')
    ca  = models.FloatField(verbose_name='Ca (%)')
    p   = models.FloatField(verbose_name='P (%)')

    # Custo em R$/kg na matéria natural
    custo_kg = models.FloatField(
        default=0.0,
        verbose_name='Custo (R$/kg MN)',
    )

    # Limite de inclusão na formulação
    limite_min_participacao = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Limite mínimo de participação (% MS)',
        help_text=(
            'Percentual mínimo (0-100) na matéria seca total. Use apenas '
            'quando houver justificativa técnica para a inclusão do ingrediente. '
            'Para dose fixa, informe o mesmo valor no limite máximo.'
        ),
    )
    limite_max_participacao = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Limite máximo de participação (% MS)',
        help_text=(
            'Percentual máximo (0-100) que este ingrediente pode representar '
            'na matéria seca total de uma formulação (ex.: bicarbonato de sódio '
            'limitado a 1.5%). Use o mesmo valor do limite mínimo para uma dose '
            'fixa. Deixe em branco para não aplicar nenhum limite.'
        ),
    )

    fonte_valadares = models.BooleanField(
        default=False,
        verbose_name='Base Valadares',
        help_text='True = ingrediente da tabela Valadares Filho (2010); False = custom do usuário.',
        db_index=True,
    )

    dt_cadastro    = models.DateTimeField(auto_now_add=True)
    dt_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        """Ordena o catálogo por classe, tipo e nome para facilitar seleção."""
        verbose_name          = 'Ingrediente'
        verbose_name_plural   = 'Ingredientes'
        ordering              = ['classificacao', 'tipo', 'nome']
        indexes = [
            models.Index(fields=['classificacao', 'tipo']),
            models.Index(fields=['fonte_valadares', 'classificacao']),
        ]

    def __str__(self):
        """Mostra nome, tipo e origem do ingrediente em listas administrativas."""
        origem = 'Valadares' if self.fonte_valadares else 'Custom'
        return f'{self.nome} [{self.get_tipo_display()} / {origem}]'


class OrigemAlteracaoPrecoChoices(models.TextChoices):
    """Indica se o preço veio do catálogo pessoal ou de uma formulação."""
    CATALOGO   = "CATALOGO",   "Banco de preços do usuário"
    FORMULACAO = "FORMULACAO", "Override local (uma receita)"


class PrecoIngredienteUsuario(models.Model):
    """
    O "banco de preços regional" do usuário (requisito #1 da Fase 2).

    Ingrediente.custo_kg NÃO é usado para resolver o preço de um
    ingrediente numa formulação — ele é compartilhado por TODOS os
    usuários (é o catálogo Valadares, read-only por design, ver
    _verificar_propriedade em ingrediente/viewsets.py). Se o preço
    regional de um produtor fosse gravado ali, vazaria para o catálogo
    de todos os outros produtores que usam o mesmo ingrediente.

    Esta tabela existe justamente para isolar isso: cada usuário tem,
    no máximo, um preço próprio por ingrediente (Valadares ou custom),
    independente de quem é o dono do Ingrediente. É o destino real do
    escopo="geral" em AtualizarPrecoIngredienteService.
    """
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='precos_ingredientes',
    )
    ingrediente = models.ForeignKey(
        Ingrediente,
        on_delete=models.CASCADE,
        related_name='precos_usuarios',
    )
    preco_kg_mn = models.FloatField(verbose_name='Preço (R$/kg MN)')
    dt_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        """Garante um único preço regional por usuário e ingrediente."""
        verbose_name        = 'Preço de Ingrediente (usuário)'
        verbose_name_plural  = 'Preços de Ingredientes (usuário)'
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'ingrediente'],
                name='unico_preco_por_usuario_ingrediente',
            ),
        ]

    def __str__(self):
        """Resume ingrediente, usuário e preço para auditoria administrativa."""
        return f'{self.ingrediente.nome} — {self.usuario} — R$ {self.preco_kg_mn:.2f}/kg'


class HistoricoPrecoIngrediente(models.Model):
    """Registro imutável de uma alteração de preço feita por um usuário."""
    ingrediente = models.ForeignKey(
        Ingrediente,
        on_delete=models.CASCADE,
        related_name='historico_precos',
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='historico_precos_ingredientes',
    )
    preco_anterior = models.FloatField(null=True)
    preco_novo = models.FloatField(null=True)
    origem_alteracao = models.CharField(
        max_length=15,
        choices=OrigemAlteracaoPrecoChoices.choices,
    )
    dt_alteracao = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Exibe primeiro as alterações de preço mais recentes."""
        verbose_name         = 'Histórico de Preço'
        verbose_name_plural   = 'Históricos de Preço'
        ordering              = ['-dt_alteracao']
