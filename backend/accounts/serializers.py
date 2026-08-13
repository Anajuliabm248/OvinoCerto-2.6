"""Validação e tradução dos dados de autenticação e perfil da API."""

from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import Usuario

DjangoUser = get_user_model()

# pylint: disable= abstract-method, no-member, too-few-public-methods


class UsuarioSerializer(serializers.ModelSerializer):
    """Expõe o perfil autenticado sem permitir elevação de privilégio pela API."""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        """Seleciona dados públicos do perfil e protege campos de identidade."""
        model = Usuario
        fields = [
            'id',
            'username',
            'nome',
            'email',
            'cpf',
            'telefone',
            'estado',
            'cidade',
            'profissao',
            'produtor_ovinos',
            'perfil',
            'is_admin',
            'is_user',
        ]
        read_only_fields = ['id', 'perfil', 'is_admin', 'is_user']

    def validate_email(self, value):
        """Normaliza o novo login e impede conflito com outra conta Django."""
        value = value.strip().lower()
        queryset = DjangoUser.objects.filter(username=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.user_id)
        if queryset.exists():
            raise serializers.ValidationError('Este e-mail já está em uso como usuário.')
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        """Mantém e-mail do perfil, username e e-mail de autenticação sincronizados."""
        novo_email = validated_data.get('email')
        if novo_email and novo_email != instance.email:
            instance.user.username = novo_email
            instance.user.email = novo_email
            instance.user.save(update_fields=['username', 'email'])
        return super().update(instance, validated_data)


class RegisterSerializer(serializers.Serializer):
    """Valida o cadastro e cria, de forma atômica, conta e perfil."""
    # Credenciais Django (usar apenas o email como username)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label='Confirmar senha')

    # Campos do perfil
    nome           = serializers.CharField(max_length=100)
    email          = serializers.EmailField(max_length=255)
    cpf            = serializers.CharField(max_length=14)
    telefone       = serializers.CharField(max_length=15)
    estado         = serializers.CharField(max_length=50)
    cidade         = serializers.CharField(max_length=50)
    profissao      = serializers.CharField(max_length=100)
    produtor_ovinos = serializers.BooleanField(default=False)

    def validate_email(self, value):
        """Normaliza o e-mail e impede duplicidade na conta ou no perfil."""
        value = value.strip().lower()
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este e-mail já está cadastrado.')
        if DjangoUser.objects.filter(username=value).exists() or \
                DjangoUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este e-mail já está em uso como usuário.')
        return value

    def validate_cpf(self, value):
        """Remove espaços laterais e impede o cadastro de CPF repetido."""
        value = value.strip()
        if Usuario.objects.filter(cpf=value).exists():
            raise serializers.ValidationError('Este CPF já está cadastrado.')
        return value

    def validate(self, attrs):
        """Confere a confirmação da senha e retira o campo auxiliar."""
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError({'password': 'As senhas não coincidem.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """Cria a conta Django e o perfil na mesma transação de banco."""
        email = validated_data.pop('email')
        password = validated_data.pop('password')

        django_user = DjangoUser.objects.create_user(
            username=email,
            email=email,
            password=password,
        )

        usuario = Usuario.objects.create(user=django_user, email=email, **validated_data)
        return usuario


class LoginSerializer(serializers.Serializer):
    """Recebe e-mail e senha e devolve a conta autenticada em ``user``."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Autentica pelo e-mail usado como username e bloqueia contas inativas."""
        user = authenticate(
            username=attrs['email'],
            password=attrs['password'],
        )
        if not user:
            raise serializers.ValidationError('Credenciais inválidas.')
        if not user.is_active:
            raise serializers.ValidationError('Conta desativada.')
        attrs['user'] = user
        return attrs
