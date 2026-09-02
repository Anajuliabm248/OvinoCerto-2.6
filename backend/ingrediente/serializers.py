"""Validação do catálogo de ingredientes e dos preços pessoais."""

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
    """Expõe composição, origem e preço do usuário que fez a requisição."""
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
        """Protege propriedade, origem e datas contra edição direta."""
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
            'limite_min_participacao',
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
            'limite_min_participacao': {
                'help_text': (
                    'Percentual mínimo (0-100) na MS. Informe somente para '
                    'inclusões tecnicamente obrigatórias. Para dose fixa, informe '
                    'o mesmo valor no limite máximo.'
                ),
            },
            'limite_max_participacao': {
                'help_text': (
                    'Percentual máximo (0-100) que este ingrediente pode representar '
                    'na matéria seca total da formulação. Deixe em branco para não '
                    'aplicar limite (ex.: bicarbonato de sódio costuma ser limitado a '
                    'cerca de 1.5%). Para dose fixa, use o mesmo valor do limite mínimo.'
                ),
            },
        }

    def validate_limite_max_participacao(self, value):
        """Aceita limite vazio ou percentual maior que zero e até 100%."""
        if value is not None and not (0.0 < value <= 100.0):
            raise serializers.ValidationError(
                'O limite máximo de participação deve estar entre 0 (exclusive) e 100%.'
            )
        return value

    def validate_limite_min_participacao(self, value):
        """Aceita mínimo vazio ou percentual entre zero e cem."""
        if value is not None and not (0.0 <= value < 100.0):
            raise serializers.ValidationError(
                'O limite mínimo de participação deve estar entre 0 e 100%.'
            )
        return value

    def validate(self, attrs):
        """Impede catálogo público editável e rejeita composição ou custo impossíveis."""

        instance = getattr(self, 'instance', None)
        if instance and instance.fonte_valadares:
            raise serializers.ValidationError(
                'Ingredientes da tabela Valadares não podem ser editados.'
            )

        campos_percentuais = ('ms', 'pb', 'ndt', 'fdn', 'ee', 'ca', 'p')
        for campo in campos_percentuais:
            if campo not in attrs:
                continue
            valor = attrs[campo]
            minimo = 0.0 if campo != 'ms' else 1e-12
            if not minimo <= valor <= 100.0 or (campo == 'ms' and valor == 0):
                mensagem = 'deve ser maior que zero e até 100%' if campo == 'ms' else 'deve estar entre 0 e 100%'
                raise serializers.ValidationError({campo: f'{campo.upper()} {mensagem}.'})
        if 'custo_kg' in attrs and attrs['custo_kg'] < 0:
            raise serializers.ValidationError({'custo_kg': 'O custo não pode ser negativo.'})
        limite_min = attrs.get(
            'limite_min_participacao',
            getattr(instance, 'limite_min_participacao', None),
        )
        limite_max = attrs.get(
            'limite_max_participacao',
            getattr(instance, 'limite_max_participacao', None),
        )
        if limite_min is not None and limite_max is not None and limite_min > limite_max:
            raise serializers.ValidationError({
                'limite_min_participacao': (
                    'O limite mínimo não pode ser maior que o limite máximo.'
                )
            })
        return attrs

    def get_preco_kg_mn(self, obj):
        """Busca o preço regional do usuário atual sem expor preços de terceiros."""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            return None

        user = request.user
        if not getattr(user, 'is_authenticated', False):
            return None

        try:
            perfil = user.perfil_usuario
        except Usuario.DoesNotExist:
            return None

        registro = PrecoIngredienteUsuario.objects.filter(usuario=perfil, ingrediente=obj).first()
        if registro:
            return registro.preco_kg_mn
        return None
