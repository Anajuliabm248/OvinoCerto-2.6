from django.contrib import admin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'cpf', 'perfil', 'produtor_ovinos')
    list_filter = ('perfil', 'produtor_ovinos')
    search_fields = ('nome', 'email', 'cpf')
