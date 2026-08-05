"""serializers de ingredientes"""

from django.db.models import OrderBy
from rest_framework import serializers
from .models import Ingrediente, PrecoIngredienteUsuario
from accounts.models import Usuario

# pylint: disable= too-few-public-methods

class AtualizarPrecoCatalogoInputSerializer(serializers.Serializer):
    """
    Corpo de PATCH /api/ingredientes/{id}/preco/.

    Sempre grava no banco de preços regional do usuário logado
    (PrecoIngredienteUsuario) — não existe conceito de "escopo" aqui,
    pois fora do contexto de uma formulação só existe um destino
    possível para o preço.
    """
    preco = serializers.FloatField(min_value=0.0, label="Preço (R$/kg MN)")


class IngredienteSerializer(serializers.ModelSerializer):
    '''serializer do ingrediente'''
    classificacao_display = serializers.CharField(
        source='get_classificacao_display', read_only=True
    )
    tipo_display = serializers.CharField(
        source='get_tipo_display', read_only=True
    )
    usuario_nome = serializers.CharField(
        source='usuario.nome', read_only=True, default=None
    )
    preco_kg_mn = serializers.SerializerMethodField(read_only=True)

    class Meta:
        '''classe meta, define os campos do serializer'''
        model = Ingrediente
        fields = [
            'id',
            'usuario',
            'usuario_nome',
            'preco_kg_mn',
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
            'limite_max_participacao',
            'fonte_valadares',
            'dt_cadastro',
            'dt_atualizacao',
        ]
        read_only_fields = [
            'id',
            'usuario',
            'preco_kg_mn',
            'fonte_valadares',
            'dt_cadastro',
            'dt_atualizacao',
        ]
        extra_kwargs = {
            'limite_max_participacao': {
                'help_text': (
                    'Percentual máximo (0-100) que este ingrediente pode representar '
                    'na matéria seca total da formulação. Deixe em branco para não '
                    'aplicar limite (ex.: bicarbonato de sódio costuma ser limitado a '
                    'cerca de 1.5%).'
                ),
            },
        }

    def validate_limite_max_participacao(self, value):
        '''Quando informado, o limite deve ser um percentual válido (0 exclusive-100].'''
        if value is not None and not (0.0 < value <= 100.0):
            raise serializers.ValidationError(
                'O limite máximo de participação deve estar entre 0 (exclusive) e 100%.'
            )
        return value

    def validate(self, attrs):
        '''Ingredientes Valadares não podem ser editados via API'''

        instance = getattr(self, 'instance', None)
        if instance and instance.fonte_valadares:
            raise serializers.ValidationError(
                'Ingredientes da tabela Valadares não podem ser editados.'
            )
        return attrs

    def get_preco_kg_mn(self, obj):
        """Retorna o preço (se houver) gravado pelo usuário para este ingrediente."""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            return None
        try:
            perfil = request.user.perfil_usuario
        except Usuario.DoesNotExist:
            return None
        registro = PrecoIngredienteUsuario.objects.filter(usuario=perfil, ingrediente=obj).first()
        if registro:
            return registro.preco_kg_mn
        return None
