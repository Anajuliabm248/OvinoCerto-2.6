from django.contrib import admin
from .models import (
    Formulacao, IngredienteFormulacao, MotorOtimizacao,
    Recomendacao, AjusteDieta, CustoViabilidade,
)


class IngredienteFormulacaoInline(admin.TabularInline):
    model  = IngredienteFormulacao
    extra  = 0
    fields = ['ingrediente', 'ms_porcent', 'ms_kg', 'mn_kg', 'custo_dia']
    readonly_fields = fields


class MotorOtimizacaoInline(admin.StackedInline):
    model  = MotorOtimizacao
    extra  = 0
    fields = ['objetivo', 'status', 'motivo_inviabilidade', 'custo_otimizado', 'dt_execucao']
    readonly_fields = fields


@admin.register(Formulacao)
class FormulacaoAdmin(admin.ModelAdmin):
    list_display  = ['id', 'titulo', 'lote', 'usuario', 'objetivo_otimizacao',
                     'custo_animal_dia', 'dt_inc']
    list_filter   = ['objetivo_otimizacao', 'dt_inc', 'lote__categoria']
    search_fields = ['titulo', 'lote__nome_lote', 'usuario__nome']
    readonly_fields = ['dt_inc', 'dt_alt']
    inlines       = [MotorOtimizacaoInline, IngredienteFormulacaoInline]
    fieldsets = (
        ('Identificação', {
            'fields': ('lote', 'usuario', 'exigencia', 'titulo',
                       'objetivo_otimizacao', 'observacoes'),
        }),
        ('Resumo nutricional', {
            'fields': ('vol_ms_percent', 'conc_ms_percent', 'mistura_conc', 'rs_kg_mn_total'),
        }),
        ('Custos', {
            'fields': ('custo_animal_dia', 'custo_lote_dia'),
        }),
        ('Datas', {
            'fields': ('dt_inc', 'dt_alt'),
        }),
    )


@admin.register(IngredienteFormulacao)
class IngredienteFormulacaoAdmin(admin.ModelAdmin):
    list_display  = ['formulacao', 'ingrediente', 'ms_porcent', 'mn_kg', 'custo_dia']
    list_filter   = ['ingrediente__tipo', 'formulacao__objetivo_otimizacao']
    search_fields = ['ingrediente__nome', 'formulacao__titulo']
    readonly_fields = ['formulacao', 'ingrediente']


@admin.register(MotorOtimizacao)
class MotorOtimizacaoAdmin(admin.ModelAdmin):
    list_display  = ['formulacao', 'objetivo', 'status', 'custo_otimizado', 'dt_execucao']
    list_filter   = ['status', 'objetivo']
    readonly_fields = ['dt_execucao', 'resultado_simplex']


@admin.register(Recomendacao)
class RecomendacaoAdmin(admin.ModelAdmin):
    list_display  = ['formulacao', 'ingrediente_sugerido', 'objetivo', 'score', 'delta_custo']
    list_filter   = ['objetivo']
    search_fields = ['ingrediente_sugerido__nome']


@admin.register(AjusteDieta)
class AjusteDietaAdmin(admin.ModelAdmin):
    list_display = ['formulacao', 'peso_ajustado', 'cms_percent',
                    'sobras_percent', 'fornecimento_unit', 'fornecimento_lote']


@admin.register(CustoViabilidade)
class CustoViabilidadeAdmin(admin.ModelAdmin):
    list_display = ['formulacao', 'peso_entrada', 'peso_saida_estimado',
                    'gmd', 'custo_total_dieta', 'preco_min_lucro']
