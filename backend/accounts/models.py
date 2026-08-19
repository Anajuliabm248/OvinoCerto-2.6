"""Perfis complementares dos usuários autenticados pelo Django.

O model nativo de autenticação guarda senha, sessão e estado da conta. Este
app mantém os dados de negócio usados pelo OvinoCerto, como contato, localidade
e perfil de acesso.
"""

from django.conf import settings
from django.db import models

# pylint: disable=too-few-public-methods, invalid-str-returned

class Perfil(models.TextChoices):
    """Papéis de negócio disponíveis para um perfil do OvinoCerto."""
    ADMIN = 'ADMIN', 'Administrador do Sistema'
    USER = 'USER', 'Usuario do Sistema'


class Usuario(models.Model):
    """Dados de negócio ligados, um para um, à conta autenticável do Django."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_usuario',
    )
    nome = models.CharField(max_length=100)
    email = models.EmailField(unique=True, db_index=True)
    cpf = models.CharField(max_length=14, unique=True)
    telefone = models.CharField(max_length=15)
    estado = models.CharField(max_length=50)
    cidade = models.CharField(max_length=50)
    profissao = models.CharField(max_length=100)
    produtor_ovinos = models.BooleanField(default=False)
    perfil = models.CharField(
        'Perfil',
        max_length=20,
        choices=Perfil.choices,
        default=Perfil.USER,
        db_index=True,
    )

    class Meta:
        """Define os nomes exibidos no admin e a ordenação por nome."""
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['nome']

    def __str__(self):
        """Usa o nome da pessoa nas telas administrativas e nos logs."""
        return self.nome

    @property
    def is_admin(self):
        """Informa se o perfil possui o papel administrativo de negócio."""
        return self.perfil == Perfil.ADMIN

    @property
    def is_user(self):
        """Informa se o perfil é um usuário comum do sistema."""
        return self.perfil == Perfil.USER

    @property
    def pode_gerenciar_usuarios(self):
        """Centraliza a regra de autorização para gerenciar outros perfis."""
        return self.perfil == Perfil.ADMIN
