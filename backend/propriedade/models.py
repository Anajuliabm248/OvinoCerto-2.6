"""Propriedades rurais que organizam os lotes de cada usuário."""

from django.db import models

from accounts.models import Usuario

# pylint: disable= invalid-str-returned, too-few-public-methods

class Propriedade(models.Model):
    """Representa uma unidade produtiva pertencente a um único perfil."""
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='propriedades',
    )
    nome = models.CharField(max_length=255)
    proprietario = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    uf = models.CharField(max_length=2)
    cidade = models.CharField(max_length=255)
    localidade = models.CharField(max_length=255)
    dt_cadastro = models.DateTimeField(auto_now_add=True)
    dt_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        """Mostra primeiro as propriedades cadastradas mais recentemente."""
        verbose_name = "Propriedade"
        verbose_name_plural = "Propriedades"
        ordering = ['-dt_cadastro'] # data de cadastro mais recente primeiro

    def __str__(self):
        """Usa o nome da propriedade em seletores e telas administrativas."""
        return self.nome
