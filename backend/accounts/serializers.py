from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Usuario

DjangoUser = get_user_model()


class UsuarioSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
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
        read_only_fields = ['id', 'is_admin', 'is_user']


class RegisterSerializer(serializers.Serializer):
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
        # Email must be unique both as Usuario.email and as Django username/email
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este e-mail já está cadastrado.')
        if DjangoUser.objects.filter(username=value).exists() or DjangoUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este e-mail já está em uso como usuário.')
        return value

    def validate_cpf(self, value):
        if Usuario.objects.filter(cpf=value).exists():
            raise serializers.ValidationError('Este CPF já está cadastrado.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError({'password': 'As senhas não coincidem.'})
        return attrs

    def create(self, validated_data):
        # Use email as the Django username
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
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth import authenticate
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