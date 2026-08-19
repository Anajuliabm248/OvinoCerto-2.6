"""Representação e validação das propriedades na API."""

from rest_framework import serializers
from .models import Propriedade

# pylint: disable= too-few-public-methods

class PropriedadeSerializer(serializers.ModelSerializer):
    """Expõe os dados da fazenda sem permitir troca direta de proprietário."""
    usuario_nome = serializers.CharField(source='usuario.nome', read_only=True)

    class Meta:
        """Protege usuário, identificador e datas preenchidos pelo servidor."""
        model = Propriedade
        fields = [
            'id',
            'usuario',
            'usuario_nome',
            'nome',
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

    def validate_uf(self, value):
        """Normaliza a sigla estadual e rejeita valores diferentes de duas letras."""
        value = value.strip().upper()
        if len(value) != 2 or not value.isalpha():
            raise serializers.ValidationError('Informe a UF com duas letras, por exemplo RS.')
        return value
