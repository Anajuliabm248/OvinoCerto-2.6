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
        # usuario é setado automaticamente via perform_create no viewset
        read_only_fields = ['id', 'usuario', 'usuario_nome', 'dt_cadastro', 'dt_atualizacao']