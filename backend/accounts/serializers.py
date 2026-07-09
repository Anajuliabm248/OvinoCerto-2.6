""" serializadores para o app accounts """

from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Usuario

DjangoUser = get_user_model()

# pylint: disable= abstract-method, no-member, too-few-public-methods


class UsuarioSerializer(serializers.ModelSerializer):
    '''Serializador para o model Usuario.'''
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        '''classe Meta, define o model e os campos a serem serializados'''
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
    '''Serializador para o registro de novos usuários.'''
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
        '''valida o email para garantir que já não está em uso'''
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este e-mail já está cadastrado.')
        if DjangoUser.objects.filter(username=value).exists() or \
                DjangoUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este e-mail já está em uso como usuário.')
        return value

    def validate_cpf(self, value):
        '''valida o cpf para garantir que já não está em uso'''
        if Usuario.objects.filter(cpf=value).exists():
            raise serializers.ValidationError('Este CPF já está cadastrado.')
        return value

    def validate(self, attrs):
        '''valida se as senhas batem'''
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError({'password': 'As senhas não coincidem.'})
        return attrs

    def create(self, validated_data):
        '''cria o usuário'''
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
    '''serializer de login'''
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
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
