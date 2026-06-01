from rest_framework import serializers
from .models import Lote


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
            'idade',
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
