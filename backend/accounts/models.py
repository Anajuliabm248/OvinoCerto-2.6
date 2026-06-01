from django.conf import settings
from django.db import models


class Perfil(models.TextChoices):
    ADMIN = 'ADMIN', 'Administrador do Sistema'
    USER = 'USER', 'Usuario do Sistema'


class Usuario(models.Model):
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
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    @property
    def is_admin(self):
        return self.perfil == Perfil.ADMIN

    @property
    def is_user(self):
        return self.perfil == Perfil.USER

    @property
    def pode_gerenciar_usuarios(self):
        return self.perfil == Perfil.ADMIN
