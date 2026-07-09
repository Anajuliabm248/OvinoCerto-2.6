"""models do app propriedade"""

from django.db import models

from accounts.models import Usuario

# pylint: disable= invalid-str-returned, too-few-public-methods

class Propriedade(models.Model):
    '''Modelo de Propriedade'''
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='propriedades',
    )
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=20, unique=True, blank=True, null=True)
    proprietario = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    uf = models.CharField(max_length=2)
    cidade = models.CharField(max_length=255)
    localidade = models.CharField(max_length=255)
    dt_cadastro = models.DateTimeField(auto_now_add=True)
    dt_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        '''classe meta, para definir o nome do modelo no admin e a ordenação padrão'''
        verbose_name = "Propriedade"
        verbose_name_plural = "Propriedades"
        ordering = ['-dt_cadastro'] # data de cadastro mais recente primeiro

    def __str__(self):
        return self.nome
