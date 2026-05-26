from django.db import models

from accounts.models import Usuario

# Create your models here.
'''
int id
int id_usuario
str nome
str cnpj (opcional)
str proprietario (faz referência ao nome do usuário)
str telefone (opcional)
str uf
str cidade
str localidade
date dt_cadastro
date dt_atualizacao
'''


class Propriedade(models.Model):
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
        verbose_name_plural = "Propriedades"
        ordering = ['-dt_cadastro'] # data de cadastro mais recente primeiro
        
    def __str__(self):
        return self.nome
    
