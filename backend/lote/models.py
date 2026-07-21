"""modelos do app de lote"""

from django.db import models

# pylint: disable=too-few-public-methods, no-member

CATEGORIA_CHOICES = [
    ('cordeiros_4_meses', 'Cordeiros(as) 4 meses'),
    ('cordeiros_8_meses', 'Cordeiros(as) 8 meses'),
    ('carneiro_4_meses', 'Carneiro 4 meses'),
    ('carneiro_8_meses', 'Carneiro 8 meses'),
    ('carneiros', 'Carneiros'),
    ('ovelhas', 'Ovelhas'),
]

FASE_CHOICES = [
    ('crescimento', 'Crescimento'),
    ('manutencao', 'Manutenção'),
    ('pre_cobricao', 'Pré-cobrição'),
    ('reproducao', 'Reprodução'),
    ('gestacao_precoce', 'Gestação precoce'),
    ('gestacao_tardia', 'Gestação tardia'),
    ('inicio_lactacao', 'Início da lactação'),
    ('meio_lactacao', 'Meio da lactação'),
    ('lactacao_tardia', 'Lactação tardia'),
]

TIPO_PARTO_CHOICES = [
    (1, '1 Cordeiro'),
    (2, '2 Cordeiros'),
    (3, '3 Cordeiros'),
    (4, '4 Cordeiros'),
    (5, '5 Cordeiros'),
]

# Fases válidas por categoria
FASES_VALIDAS = {
    'cordeiros_4_meses': ['crescimento'],
    'cordeiros_8_meses': ['crescimento'],
    'carneiro_4_meses': ['crescimento'],
    'carneiro_8_meses': ['crescimento'],
    'carneiros': ['manutencao', 'pre_cobricao', 'reproducao'],
    'ovelhas': [
        'manutencao', 'pre_cobricao', 'reproducao', 'gestacao_precoce',
        'gestacao_tardia', 'inicio_lactacao', 'meio_lactacao', 'lactacao_tardia',
    ],
}

# Fases que exigem tipo_parto e dias_fase (apenas ovelhas)
FASES_COM_PARTO_E_DIAS = [
    'gestacao_precoce', 'gestacao_tardia',
    'inicio_lactacao', 'meio_lactacao', 'lactacao_tardia',
]

class Lote(models.Model):
    '''Model para representar um lote de animais em uma propriedade.'''
    propriedade = models.ForeignKey(
        'propriedade.Propriedade',
        on_delete=models.CASCADE,
        related_name='lotes',
    )
    nome_lote = models.CharField(max_length=200, verbose_name='Nome do lote')
    raca = models.CharField(max_length=100, blank=True, null=True, verbose_name='Raça')
    sistema = models.CharField(max_length=100, blank=True, null=True,
                               verbose_name='Sistema de criação')
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, verbose_name='Categoria')
    fase = models.CharField(max_length=20, choices=FASE_CHOICES, verbose_name='Fase produtiva')
    tipo_parto = models.PositiveSmallIntegerField(
        choices=TIPO_PARTO_CHOICES,
        blank=True, null=True,
        verbose_name='Tipo de parto',
        help_text='Requerido para fases de gestação e lactação.',
    )
    pv_nascer_kg = models.FloatField(
        blank=True, null=True,
        verbose_name='Peso vivo ao nascer (kg)',
    )
    producao_leite_kg_dia = models.FloatField(
        blank=True, null=True,
        verbose_name='Produção de leite (kg/dia)',
    )
    peso_vivo = models.FloatField(verbose_name='Peso vivo médio (kg)')
    gmd_esperado = models.FloatField(verbose_name='Ganho médio por dia esperado (kg/dia)')
    num_animais = models.PositiveIntegerField(verbose_name='Número de animais')
    pv_percentual = models.FloatField(
        blank=True, null=True,
        verbose_name='% Peso vivo',
        help_text='Percentual do peso vivo utilizado no cálculo de CMS.',
    )
    dt_cadastro = models.DateTimeField(auto_now_add=True)
    dt_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        '''classe meta, define o nome do model e a ordenação padrão'''
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'
        ordering = ['-dt_cadastro']

    def __str__(self):
        return f"{self.nome_lote} ({self.propriedade.nome})"
