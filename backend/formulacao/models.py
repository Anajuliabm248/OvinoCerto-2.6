from django.db import models
from lote.models import Lote
from ingrediente.models import Ingrediente
from accounts.models import Usuario
from exigencia_nrc.models import ExigenciaNRC


OBJETIVO_CHOICES = [
    ('CUSTO', 'Mínimo custo'),
    ('PB',    'Máxima proteína bruta'),
    ('FDN',   'Mínimo FDN'),
]

STATUS_CHOICES = [
    ('sucesso',  'Sucesso'),
    ('inviavel', 'Inviável'),
]


class Formulacao(models.Model):
    lote = models.ForeignKey(
        Lote, on_delete=models.CASCADE,
        related_name='formulacoes', verbose_name='Lote',
    )
    usuario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True,
        related_name='formulacoes', verbose_name='Usuário',
    )
    exigencia = models.ForeignKey(
        ExigenciaNRC, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='formulacoes', verbose_name='Exigência NRC',
    )

    titulo               = models.CharField(max_length=200, verbose_name='Título')
    objetivo_otimizacao  = models.CharField(
        max_length=5, choices=OBJETIVO_CHOICES,
        verbose_name='Objetivo de otimização',
    )
    observacoes = models.TextField(blank=True, null=True, verbose_name='Observações')

    # Resumo vol/conc (percentuais da MS)
    vol_ms_percent  = models.FloatField(null=True, blank=True, verbose_name='Volumoso % MS')
    conc_ms_percent = models.FloatField(null=True, blank=True, verbose_name='Concentrado % MS')
    mistura_conc    = models.FloatField(null=True, blank=True, verbose_name='Mistura concentrado (kg MS/dia)')
    rs_kg_mn_total  = models.FloatField(null=True, blank=True, verbose_name='Total MN (kg/animal/dia)')

    # Custos
    custo_animal_dia = models.FloatField(null=True, blank=True, verbose_name='Custo animal/dia (R$)')
    custo_lote_dia   = models.FloatField(null=True, blank=True, verbose_name='Custo lote/dia (R$)')

    dt_inc = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    dt_alt = models.DateTimeField(auto_now=True,     verbose_name='Alterado em')

    class Meta:
        verbose_name        = 'Formulação'
        verbose_name_plural = 'Formulações'
        ordering            = ['-dt_inc']
        indexes = [
            models.Index(fields=['lote', '-dt_inc']),
            models.Index(fields=['usuario', '-dt_inc']),
        ]

    def __str__(self):
        return f'{self.titulo} – {self.lote.nome_lote}'


class IngredienteFormulacao(models.Model):
    formulacao = models.ForeignKey(
        Formulacao, on_delete=models.CASCADE,
        related_name='ingredientes_formulacao',
    )
    ingrediente = models.ForeignKey(
        Ingrediente, on_delete=models.SET_NULL, null=True,
        related_name='ingredientes_formulacao',
    )

    ms_porcent = models.FloatField(verbose_name='Participação % MS')
    ms_kg      = models.FloatField(verbose_name='MS kg/animal/dia')
    mn_kg      = models.FloatField(verbose_name='MN kg/animal/dia')
    pb_kg      = models.FloatField(verbose_name='PB kg/dia')
    ndt_kg     = models.FloatField(verbose_name='NDT kg/dia')
    fdn_kg     = models.FloatField(verbose_name='FDN kg/dia')
    ee_kg      = models.FloatField(verbose_name='EE kg/dia')
    ca_kg      = models.FloatField(verbose_name='Ca kg/dia')
    p_kg       = models.FloatField(verbose_name='P kg/dia')
    custo_dia  = models.FloatField(verbose_name='Custo/dia R$')

    class Meta:
        verbose_name        = 'Ingrediente na Formulação'
        verbose_name_plural = 'Ingredientes na Formulação'
        ordering            = ['-ms_porcent']

    def __str__(self):
        nome = self.ingrediente.nome if self.ingrediente else '?'
        return f'{nome}: {self.ms_porcent:.1f}% MS'


class MotorOtimizacao(models.Model):
    formulacao = models.OneToOneField(
        Formulacao, on_delete=models.CASCADE,
        related_name='motor_otimizacao',
    )
    objetivo             = models.CharField(max_length=5, choices=OBJETIVO_CHOICES)
    status               = models.CharField(max_length=10, choices=STATUS_CHOICES)
    motivo_inviabilidade = models.TextField(blank=True, null=True)
    custo_otimizado      = models.FloatField(null=True, blank=True)
    restricoes_aplicadas = models.JSONField(default=list, blank=True)
    resultado_simplex    = models.JSONField(default=dict, blank=True)
    dt_execucao          = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Motor de Otimização'
        verbose_name_plural = 'Motores de Otimização'

    def __str__(self):
        return f'Otimização [{self.status}] – {self.formulacao.titulo}'


class Recomendacao(models.Model):
    formulacao = models.ForeignKey(
        Formulacao, on_delete=models.CASCADE,
        related_name='recomendacoes',
    )
    ingrediente_sugerido = models.ForeignKey(
        Ingrediente, on_delete=models.CASCADE,
        related_name='sugerido_em',
    )
    ingrediente_substituido = models.ForeignKey(
        Ingrediente, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='substituido_em',
    )
    objetivo             = models.CharField(max_length=5, choices=OBJETIVO_CHOICES)
    score                = models.FloatField(default=0.0)
    delta_custo          = models.FloatField(default=0.0)
    delta_pb             = models.FloatField(default=0.0)
    delta_ndt            = models.FloatField(default=0.0)
    distancia_euclidiana = models.FloatField(default=0.0)
    dt_geracao           = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Recomendação'
        verbose_name_plural = 'Recomendações'
        ordering            = ['-score']

    def __str__(self):
        nome = self.ingrediente_sugerido.nome if self.ingrediente_sugerido else '?'
        return f'Rec: {nome} (score={self.score:.2f})'


class AjusteDieta(models.Model):
    formulacao = models.OneToOneField(
        Formulacao, on_delete=models.CASCADE,
        related_name='ajuste_dieta',
    )
    peso_ajustado    = models.FloatField(verbose_name='Peso ajustado (kg)')
    cms_percent      = models.FloatField(verbose_name='CMS (% PV)')
    lote_un          = models.PositiveIntegerField(verbose_name='Animais no lote')
    sobras_percent   = models.FloatField(default=5.0,  verbose_name='Sobras (%)')
    num_refeicoes    = models.PositiveIntegerField(default=2, verbose_name='Nº refeições/dia')
    perda_alimentos  = models.FloatField(default=0.0,  verbose_name='Perda de alimentos (%)')
    fornecimento_unit = models.FloatField(verbose_name='Fornecimento/animal (kg MN/dia)')
    fornecimento_lote = models.FloatField(verbose_name='Fornecimento/lote (kg MN/dia)')

    class Meta:
        verbose_name        = 'Ajuste de Dieta'
        verbose_name_plural = 'Ajustes de Dieta'

    def __str__(self):
        return f'Ajuste – {self.formulacao.titulo}'


class CustoViabilidade(models.Model):
    formulacao = models.OneToOneField(
        Formulacao, on_delete=models.CASCADE,
        related_name='custo_viabilidade',
    )
    peso_entrada           = models.FloatField(verbose_name='Peso entrada (kg)')
    peso_saida_estimado    = models.FloatField(verbose_name='Peso saída estimado (kg)')
    num_animais            = models.PositiveIntegerField(verbose_name='Nº animais')
    gmd                    = models.FloatField(verbose_name='GMD (kg/dia)')
    estimativa_permanencia = models.PositiveIntegerField(verbose_name='Permanência estimada (dias)')
    cms                    = models.FloatField(verbose_name='CMS (kg/dia)')
    perda_alimentos        = models.FloatField(default=0.0, verbose_name='Perda de alimentos (%)')
    valor_kg_ovino         = models.FloatField(default=0.0, verbose_name='Valor R$/kg PV')
    custo_total_dieta      = models.FloatField(verbose_name='Custo total dieta (R$)')
    preco_min_lucro        = models.FloatField(default=0.0, verbose_name='Preço mínimo p/ lucro (R$/kg)')

    class Meta:
        verbose_name        = 'Custo e Viabilidade'
        verbose_name_plural = 'Custos e Viabilidades'

    def __str__(self):
        return f'Viabilidade – {self.formulacao.titulo}'
