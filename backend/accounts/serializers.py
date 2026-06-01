from rest_framework import serializers
from .models import Usuario


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
