"""Configurações do admin do app propriedade"""

from django.contrib import admin
from .models import Propriedade
# Register your models here.

@admin.register(Propriedade)
class PropriedadeAdmin(admin.ModelAdmin):
    '''Configurações do admin do app propriedade'''
    list_display  = ('nome', 'usuario', 'uf', 'cidade', 'dt_cadastro',)
    list_filter   = ('uf',)
    search_fields = ('nome', 'proprietario', 'cidade',)
