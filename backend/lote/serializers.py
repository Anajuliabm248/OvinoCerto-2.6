from rest_framework import serializers
from .models import FASES_COM_PARTO_E_DIAS, FASES_VALIDAS, FASE_CHOICES, Lote

FASE_LABELS = dict(FASE_CHOICES)


class LoteSerializer(serializers.ModelSerializer):
    propriedade_nome = serializers.CharField(source='propriedade.nome', read_only=True)
    
    class Meta:
        model = Lote
        fields = [
            'id',
            'propriedade',
            'propriedade_nome',
            'nome_lote',
            'raca',
            'sistema',
            'categoria',
            'fase',
            'tipo_parto',
            'dias_fase',
            'peso_vivo',
            'gmd_esperado',
            'num_animais',
            'pv_percentual',
            'dt_cadastro',
            'dt_atualizacao',
        ]
        read_only_fields = ['id', 'dt_cadastro', 'dt_atualizacao']

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        categoria = attrs.get('categoria', getattr(instance, 'categoria', None))
        fase = attrs.get('fase', getattr(instance, 'fase', None))
        tipo_parto = attrs.get('tipo_parto', getattr(instance, 'tipo_parto', None))
        dias_fase = attrs.get('dias_fase', getattr(instance, 'dias_fase', None))

        if categoria and fase:
            fases_permitidas = FASES_VALIDAS.get(categoria, [])
            if fases_permitidas and fase not in fases_permitidas:
                opcoes = ', '.join(FASE_LABELS.get(valor, valor) for valor in fases_permitidas)
                raise serializers.ValidationError({
                    'fase': (
                        f'A fase "{FASE_LABELS.get(fase, fase)}" não é válida para esta categoria. '
                        f'Opções: {opcoes}.'
                    )
                })

        if fase in FASES_COM_PARTO_E_DIAS:
            errors = {}
            if categoria != 'ovelhas':
                errors['fase'] = 'Fases de gestação e lactação são válidas apenas para ovelhas.'
            if not tipo_parto:
                errors['tipo_parto'] = 'Informe o tipo de parto para esta fase.'
            if not dias_fase:
                errors['dias_fase'] = 'Informe os dias na fase para esta fase.'
            if errors:
                raise serializers.ValidationError(errors)
        else:
            attrs['tipo_parto'] = None
            attrs['dias_fase'] = None

        return attrs
