"""serializers do app de propriedade"""

from rest_framework import serializers
from .models import Propriedade

# pylint: disable= too-few-public-methods

class PropriedadeSerializer(serializers.ModelSerializer):
    '''configuração do serializer de propriedade'''
    usuario_nome = serializers.CharField(source='usuario.nome', read_only=True)

    class Meta:
        '''classe meta para definir os campos do serializer e os campos somente leitura'''
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
        # usuario é setado automaticamente via perform_create no viewset
        read_only_fields = ['id', 'usuario', 'usuario_nome', 'dt_cadastro', 'dt_atualizacao']
