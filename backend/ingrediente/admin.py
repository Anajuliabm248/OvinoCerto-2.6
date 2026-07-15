"""Configuração do admin para o modelo Ingrediente."""

from django.contrib import admin
from .models import Ingrediente

# pylint: disable= protected-access

@admin.register(Ingrediente)
class IngredienteAdmin(admin.ModelAdmin):
    '''configuração do admin para o modelo Ingrediente'''

    list_display = ('nome', 'classificacao', 'tipo', 'ms', 'pb',
                    'ndt', 'custo_kg', 'limite_max_participacao', 'fonte_valadares', 'usuario',)
    list_filter = ('classificacao', 'tipo', 'fonte_valadares',)
    search_fields = ('nome',)
    readonly_fields = ('fonte_valadares', 'dt_cadastro', 'dt_atualizacao',)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.fonte_valadares:
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields
