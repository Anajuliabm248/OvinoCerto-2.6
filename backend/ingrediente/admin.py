"""Configuração do admin para o modelo Ingrediente."""

from django.contrib import admin
from .models import CAMPOS_LIMITES_PARTICIPACAO, Ingrediente

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
        """Em itens Valadares, libera somente os dois limites globais."""
        if obj and obj.fonte_valadares:
            return [
                campo.name
                for campo in self.model._meta.fields
                if campo.name not in CAMPOS_LIMITES_PARTICIPACAO
            ]
        return self.readonly_fields
