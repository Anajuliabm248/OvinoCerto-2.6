from django.db import models

CATEGORIA_CHOICES = [
    ('cordeiro', 'Cordeiro'),
    ('carneiro', 'Carneiro'),
    ('ovelha', 'Ovelha'),
]

IDADE_CHOICES = [
    ('ate_4_meses', '0–4 meses'),
    ('ate_8_meses', '5–8 meses'),
    ('ate_12_meses', '9–12 meses'),
    ('mais_12_meses', '13 meses ou mais'),
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

# Fases válidas por categoria e faixa de idade
FASES_VALIDAS = {
    'cordeiro': {
        'ate_4_meses': ['crescimento'],
        'ate_8_meses': ['crescimento'],
        'ate_12_meses': ['crescimento'],
        'mais_12_meses': ['crescimento'],
    },
    'carneiro': {
        'ate_4_meses': ['crescimento'],
        'ate_8_meses': ['crescimento'],
        'ate_12_meses': ['crescimento', 'manutencao'],
        'mais_12_meses': ['manutencao', 'pre_cobricao'],
    },
    'ovelha': {
        'ate_4_meses': ['crescimento'],
        'ate_8_meses': ['crescimento'],
        'ate_12_meses': ['crescimento', 'manutencao'],
        'mais_12_meses': [
            'manutencao', 'reproducao', 'gestacao_precoce',
            'gestacao_tardia', 'inicio_lactacao', 'meio_lactacao', 'lactacao_tardia',
        ],
    },
}

# Fases que exigem tipo_parto e dias_fase (apenas ovelhas)
FASES_COM_PARTO_E_DIAS = [
    'gestacao_precoce', 'gestacao_tardia',
    'inicio_lactacao', 'meio_lactacao', 'lactacao_tardia',
]


class Lote(models.Model):
    propriedade = models.ForeignKey(
        'propriedade.Propriedade',
        on_delete=models.CASCADE,
        related_name='lotes',
    )
    nome_lote = models.CharField(max_length=200, verbose_name='Nome do lote')
    raca = models.CharField(max_length=100, blank=True, null=True, verbose_name='Raça')
    sistema = models.CharField(max_length=100, blank=True, null=True, verbose_name='Sistema de criação')
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, verbose_name='Categoria')
    idade = models.CharField(max_length=20, choices=IDADE_CHOICES, verbose_name='Faixa etária')
    fase = models.CharField(max_length=20, choices=FASE_CHOICES, verbose_name='Fase produtiva')
    tipo_parto = models.PositiveSmallIntegerField(
        choices=TIPO_PARTO_CHOICES,
        blank=True, null=True,
        verbose_name='Tipo de parto',
        help_text='Requerido para fases de gestação e lactação.',
    )
    dias_fase = models.PositiveIntegerField(
        blank=True, null=True,
        verbose_name='Dias na fase',
        help_text='Número de dias na fase atual (requerido para gestação e lactação).',
    )
    peso_vivo = models.FloatField(verbose_name='Peso vivo médio (kg)')
    gmd_esperado = models.FloatField(verbose_name='GMD esperado (kg/dia)')
    num_animais = models.PositiveIntegerField(verbose_name='Número de animais')
    pv_percentual = models.FloatField(
        blank=True, null=True,
        verbose_name='% Peso vivo',
        help_text='Percentual do peso vivo utilizado no cálculo de CMS.',
    )
    dt_cadastro = models.DateTimeField(auto_now_add=True)
    dt_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'
        ordering = ['-dt_cadastro']

    def __str__(self):
        return f"{self.nome_lote} ({self.propriedade.nome})"