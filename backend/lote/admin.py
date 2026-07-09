"""configuração do admin para o modelo Lote"""

from django.contrib import admin
from .models import Lote

# Register your models here.

@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    '''Configuração do admin para o modelo Lote.'''
    list_display  = ('nome_lote', 'propriedade', 'categoria', 'fase', 'peso_vivo', 'num_animais')
    list_filter   = ('categoria', 'fase')
    search_fields = ('nome_lote', 'raca', 'sistema')
