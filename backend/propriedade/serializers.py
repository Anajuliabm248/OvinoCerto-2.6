from rest_framework import serializers
from .models import Propriedade


class PropriedadeSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source='usuario.nome', read_only=True)
    
    class Meta:
        model = Propriedade
        fields = [
            'id',
            'usuario',
            'usuario_nome',
            'nome',
            'cnpj',
            'proprietario',
            'telefone',
            'uf',
            'cidade',
            'localidade',
            'dt_cadastro',
            'dt_atualizacao',
        ]
        read_only_fields = ['id', 'dt_cadastro', 'dt_atualizacao']
