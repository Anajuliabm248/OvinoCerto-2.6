from rest_framework import serializers
from .models import Ingrediente


class IngredienteSerializer(serializers.ModelSerializer):
    classificacao_display = serializers.CharField(
        source='get_classificacao_display', read_only=True
    )
    tipo_display = serializers.CharField(
        source='get_tipo_display', read_only=True
    )
    usuario_nome = serializers.CharField(
        source='usuario.nome', read_only=True, default=None
    )

    class Meta:
        model = Ingrediente
        fields = [
            'id',
            'usuario',
            'usuario_nome',
            'classificacao',
            'classificacao_display',
            'tipo',
            'tipo_display',
            'nome',
            'ms',
            'pb',
            'ndt',
            'fdn',
            'ee',
            'ca',
            'p',
            'custo_kg',
            'fonte_valadares',
            'dt_cadastro',
            'dt_atualizacao',
        ]
        read_only_fields = [
            'id',
            'usuario',
            'fonte_valadares',
            'dt_cadastro',
            'dt_atualizacao',
        ]

    def validate(self, attrs):
        # Ingredientes Valadares não podem ser editados via API
        instance = getattr(self, 'instance', None)
        if instance and instance.fonte_valadares:
            raise serializers.ValidationError(
                'Ingredientes da tabela Valadares não podem ser editados.'
            )
        return attrs