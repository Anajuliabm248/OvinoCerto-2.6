""" models do app de ingrediente"""

from django.db import models
import numpy as np
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

    - fonte_valadares=True  →  ingrediente da base do excel, read-only
    - fonte_valadares=False →  ingrediente customizado pelo usuário
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

    fonte_valadares = models.BooleanField(
        default=False,
        verbose_name='Base Valadares',
        help_text='True = ingrediente da tabela Valadares Filho (2010); False = custom do usuário.',
        db_index=True,
    )

    dt_cadastro    = models.DateTimeField(auto_now_add=True)
    dt_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        '''classe meta, define o nome do model e a ordenação padrão'''
        verbose_name          = 'Ingrediente'
        verbose_name_plural   = 'Ingredientes'
        ordering              = ['classificacao', 'tipo', 'nome']
        indexes = [
            models.Index(fields=['classificacao', 'tipo']),
            models.Index(fields=['fonte_valadares', 'classificacao']),
        ]

    def __str__(self):
        origem = 'Valadares' if self.fonte_valadares else 'Custom'
        return f'{self.nome} [{self.get_tipo_display()} / {origem}]'

    def to_vetor_nutricional(self):
        """Retorna array numpy com [pb, ndt, fdn, ee, ca, p] em %."""
        return np.array([self.pb, self.ndt, self.fdn, self.ee, self.ca, self.p])
