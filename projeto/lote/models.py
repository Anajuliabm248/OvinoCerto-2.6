from django.db import models

# Create your models here.

CATEGORIA_CHOICES = [
    ('cordeiro', 'Cordeiro'),
    ('carneiro', 'Carneiro'),
    ('ovelha', 'Ovelha'),
]
IDADE_CHOICES = [
    ('ate_4_meses', '0-4 meses'),
    ('ate_8_meses', '5-8 meses'),
    ('ate_12_meses', '9-12 meses'),
    ('mais_12_meses', '13 meses ou mais'),
]

FASE_CHOICES = [
    ('crescimento', 'Crescimento'),
    ('manutencao', 'Manutenção'),
    ('pre_cobricao', 'Pré-cobrição'),
    ('reproducao', 'Reprodução'),
    ('gestacao_precoce', 'Gestação'),
    ('gestacao_tardia', 'Gestação tardia'),
    ('inicio_lactacao', 'Início da lactação'),
    ('meio_lactacao', 'Meio da lactação'),
    ('lactacao_tardia', 'Lactação tardia'),
]

TIPO_PARTO_CHOICES = [
    ('1', '1 Cordeiro'),
    ('2', '2 Cordeiros'),
    ('3', '3 Cordeiros'),
    ('4', '4 Cordeiros'),
    ('5', '5 Cordeiros'),
]

FASES_VALIDAS = {
    'cordeiro': {
        'ate_4_meses': ['crescimento'],
        'ate_8_meses': ['crescimento'],
        'mais_8_meses': ['crescimento'],
    },
    'carneiro': {
        'ate_4_meses': ['crescimento'],
        'ate_8_meses': ['crescimento'],
        'mais_8_meses': ['manutencao', 'pre_cobricao'],
    },
    'ovelha': {
        'ate_4_meses': ['crescimento'],
        'ate_8_meses': ['crescimento'],
        'mais_8_meses': [
            'manutencao', 'reproducao', 'gestacao_precoce',
            'gestacao_tardia', 'inicio_lactacao', 'meio_lactacao', 'lactacao_tardia',
        ],
    },
}

# Fases de ovelha que exigem tipo_parto e dias_fase
FASES_COM_PARTO_E_DIAS = [
    'gestacao_precoce', 'gestacao_tardia',
    'inicio_lactacao', 'meio_lactacao', 'lactacao_tardia',
]

class Lote(models.Model):
    propriedade = models.ForeignKey(
        'propriedade.Propriedade', 
        on_delete=models.CASCADE,
        related_name='lotes',)
    
    nome_lote = models.CharField(max_length=200)
    raca = models.CharField(max_length=100, blank=True, null=True)
    sistema = models.CharField(max_length=100, blank=True, null=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    idade = models.CharField(max_length=20, choices=IDADE_CHOICES)
    fase = models.CharField(max_length=20, choices=FASE_CHOICES)
    
    tipo_parto = models.PositiveSmallIntegerField(
        choices=TIPO_PARTO_CHOICES, 
        blank=True, 
        null=True
    )
    dias_fase = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Número de dias na fase atual (requerido para fases de gestação e lactação)"
    )
    
    peso_vivo = models.FloatField(help_text="Peso vivo médio dos animais do lote (kg)")
    gmd_esperado = models.FloatField(help_text="Ganho médio diário esperado para o lote (kg/dia)")
    num_animais = models.PositiveIntegerField(help_text="Número de animais no lote")
    pv_percentual = models.FloatField(help_text="Percentual do peso vivo em relação ao peso vivo ideal (%)", blank=True, null=True)
    dt_cadastro = models.DateTimeField(auto_now_add=True)
    dt_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Lote"
        verbose_name_plural = "Lotes"
        ordering = ['-dt_cadastro']
        
    def __str__(self):
        return f"{self.nome_lote} ({self.propriedade.nome_propriedade})"
    