from rest_framework import serializers
from ingrediente.serializers import IngredienteSerializer
from lote.serializers import LoteSerializer
from exigencia_nrc.serializers import ExigenciaNRCSerializer
from .models import (
    Formulacao, IngredienteFormulacao, MotorOtimizacao,
    Recomendacao, AjusteDieta, CustoViabilidade,
    OBJETIVO_CHOICES,
)

OBJETIVO_KEYS = [k for k, _ in OBJETIVO_CHOICES]

class FormulacaoCreateSerializer(serializers.Serializer):
    """Dados de entrada para criar uma formulação."""
    lote_id                  = serializers.IntegerField()
    titulo                   = serializers.CharField(max_length=200)
    objetivo_otimizacao      = serializers.ChoiceField(choices=OBJETIVO_KEYS)
    observacoes              = serializers.CharField(required=False, allow_blank=True, default='')
    ingredientes_selecionados = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        default=list,
        help_text='IDs dos ingredientes a incluir. Vazio = todos disponíveis.',
    )

    def validate_objetivo_otimizacao(self, value):
        return value.upper()


class IngredienteFormulacaoSerializer(serializers.ModelSerializer):
    ingrediente = IngredienteSerializer(read_only=True)

    class Meta:
        model  = IngredienteFormulacao
        fields = [
            'ingrediente',
            'ms_porcent', 'ms_kg', 'mn_kg',
            'pb_kg', 'ndt_kg', 'fdn_kg', 'ee_kg', 'ca_kg', 'p_kg',
            'custo_dia',
        ]


class MotorOtimizacaoSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = MotorOtimizacao
        fields = [
            'objetivo', 'status', 'status_display',
            'motivo_inviabilidade', 'custo_otimizado',
            'restricoes_aplicadas', 'dt_execucao',
        ]


class RecomendacaoSerializer(serializers.ModelSerializer):
    ingrediente_sugerido    = IngredienteSerializer(read_only=True)
    ingrediente_substituido = IngredienteSerializer(read_only=True)

    class Meta:
        model  = Recomendacao
        fields = [
            'ingrediente_sugerido', 'ingrediente_substituido',
            'objetivo', 'score',
            'delta_custo', 'delta_pb', 'delta_ndt',
            'distancia_euclidiana', 'dt_geracao',
        ]


class AjusteDietaSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AjusteDieta
        fields = [
            'peso_ajustado', 'cms_percent', 'lote_un',
            'sobras_percent', 'num_refeicoes', 'perda_alimentos',
            'fornecimento_unit', 'fornecimento_lote',
        ]


class CustoViabilidadeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CustoViabilidade
        fields = [
            'peso_entrada', 'peso_saida_estimado', 'num_animais',
            'gmd', 'estimativa_permanencia', 'cms', 'perda_alimentos',
            'valor_kg_ovino', 'custo_total_dieta', 'preco_min_lucro',
        ]


class FormulacaoDetailSerializer(serializers.ModelSerializer):
    lote      = LoteSerializer(read_only=True)
    exigencia = ExigenciaNRCSerializer(read_only=True)
    objetivo_otimizacao_display = serializers.CharField(
        source='get_objetivo_otimizacao_display', read_only=True,
    )

    motor_otimizacao       = MotorOtimizacaoSerializer(read_only=True)
    ingredientes_formulacao = IngredienteFormulacaoSerializer(many=True, read_only=True)
    recomendacoes          = RecomendacaoSerializer(many=True, read_only=True)
    ajuste_dieta           = AjusteDietaSerializer(read_only=True)
    custo_viabilidade      = CustoViabilidadeSerializer(read_only=True)

    # Atendimento nutricional calculado na hora (sem tabela extra)
    atendimento_nutricional = serializers.SerializerMethodField()

    class Meta:
        model  = Formulacao
        fields = [
            'id', 'titulo', 'objetivo_otimizacao', 'objetivo_otimizacao_display',
            'observacoes', 'lote', 'exigencia',
            # Totais
            'vol_ms_percent', 'conc_ms_percent', 'mistura_conc',
            'rs_kg_mn_total', 'custo_animal_dia', 'custo_lote_dia',
            # Relacionados
            'motor_otimizacao',
            'ingredientes_formulacao',
            'atendimento_nutricional',
            'recomendacoes',
            'ajuste_dieta',
            'custo_viabilidade',
            'dt_inc', 'dt_alt',
        ]

    def get_atendimento_nutricional(self, obj):
        """
        Compara os nutrientes obtidos com as exigências NRC.

        Fórmula: nutriente_% = (Σ nutriente_kg[i]) / cms_kg × 100

        Usa os valores kg já persistidos em IngredienteFormulacao para
        evitar erro de arredondamento acumulado via ms_porcent (2 casas).
        """
        if not obj.exigencia:
            return {}

        # calcula o atendimento nutricional comparando 
        # o que a dieta fornece vs o que o nrc exige
        cms_kg = obj.exigencia.cms_kg
        if not cms_kg or cms_kg <= 0:
            return {}

        # Soma kg/dia de cada nutriente a partir dos registros salvos
        totais = {n: 0.0 for n in ('PB', 'NDT', 'FDN', 'EE', 'Ca', 'P')}
        for inf in obj.ingredientes_formulacao.all():
            totais['PB']  += inf.pb_kg
            totais['NDT'] += inf.ndt_kg
            totais['FDN'] += inf.fdn_kg
            totais['EE']  += inf.ee_kg
            totais['Ca']  += inf.ca_kg
            totais['P']   += inf.p_kg

        # Converter kg/dia → % da MS:  nutriente% = (kg/dia) / CMS × 100
        for nut in totais:
            totais[nut] = totais[nut] / cms_kg * 100

        ex = obj.exigencia
        TOL = 0.05

        def _entry(obtido, exigido, operador):
            if exigido is None:
                return {'obtido': round(obtido, 2), 'exigido': None, 'atende': None}
            if operador == '>=':
                atende = obtido >= exigido - TOL
            elif operador == '<=':
                atende = obtido <= exigido + TOL
            else:
                atende = abs(obtido - exigido) <= TOL
            return {'obtido': round(obtido, 2), 'exigido': exigido, 'atende': atende}

        return {
            'PB':  _entry(totais['PB'],  ex.pb_percentual,  '>='),
            'NDT': _entry(totais['NDT'], ex.ndt_percentual, '>='),
            'FDN': _entry(totais['FDN'], ex.fdn_percentual, '<='),
            'EE':  _entry(totais['EE'],  ex.ee_percentual,  '>='),
            'Ca':  _entry(totais['Ca'],  ex.ca_percentual,  '>='),
            'P':   _entry(totais['P'],   ex.p_percentual,   '>='),
        }


class FormulacaoListSerializer(serializers.ModelSerializer):
    """Versão resumida para listagem."""
    lote_nome          = serializers.CharField(source='lote.nome_lote', read_only=True)
    objetivo_display   = serializers.CharField(
        source='get_objetivo_otimizacao_display', read_only=True,
    )
    status_motor = serializers.SerializerMethodField()

    class Meta:
        model  = Formulacao
        fields = [
            'id', 'titulo', 'lote_nome', 'objetivo_otimizacao',
            'objetivo_display', 'status_motor',
            'custo_animal_dia', 'custo_lote_dia',
            'vol_ms_percent', 'conc_ms_percent',
            'dt_inc',
        ]

    def get_status_motor(self, obj):
        try:
            return obj.motor_otimizacao.status
        except Exception:
            return None
