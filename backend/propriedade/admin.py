from django.contrib import admin
from .models import Propriedade
# Register your models here.

@admin.register(Propriedade)
class PropriedadeAdmin(admin.ModelAdmin):
    list_display  = ('nome', 'usuario', 'uf', 'cidade', 'dt_cadastro',)
    list_filter   = ('uf',)
    search_fields = ('nome', 'cnpj', 'proprietario', 'cidade',)
