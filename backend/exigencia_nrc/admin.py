''' configurações do admin para o modelo ExigenciaNRC '''

from django.contrib import admin
from .models import ExigenciaNRC
# Register your models here.

@admin.register(ExigenciaNRC)
class ExigenciaNRCAdmin(admin.ModelAdmin):
    '''configurações do admin para o model ExigenciaNRC'''
    list_display  = ('categoria', 'fase', 'pv_kg', 'tipo_parto', 'gmd_kg', 'cms_kg')
    list_filter   = ('categoria', 'fase')
    search_fields = ('categoria', 'fase')
    ordering = ('categoria', 'fase', 'pv_kg', 'gmd_kg')
