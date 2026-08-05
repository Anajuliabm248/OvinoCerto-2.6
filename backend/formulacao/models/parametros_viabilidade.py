"""
Model para os parâmetros de simulação de custo/viabilidade de uma
formulação (Quadros 9-14 da planilha "Custos e Viabilidade da Dieta").

1:1 com Formulacao — mesmo padrão de ExigenciaConfigurada. É uma
CÓPIA editável, populada com defaults a partir de Lote/ExigenciaConfigurada
na criação, mas nunca sincronizada de volta: editar estes valores serve
só para simular cenários econômicos, nunca altera a formulação
nutricional, o Lote ou a ExigenciaConfigurada (arquitetura, seção 15).

cms_percentual_pv é DELIBERADAMENTE distinto de
ExigenciaConfigurada.cms_kg — ver docstring de
formulacao/engines/motor_viabilidade.py para a justificativa completa.
Não renomeie para "cms_kg"/"cms_percentual" sem esse contexto; a
proximidade de nomes com o campo nutricional é o principal risco de
um bug futuro de confusão de conceitos.
"""

from django.db import models

from .formulacao import Formulacao

# pylint: disable= too-few-public-methods, no-member


class ParametrosViabilidade(models.Model):

    formulacao = models.OneToOneField(
        Formulacao,
        on_delete=models.CASCADE,
        related_name="parametros_viabilidade",
    )

    # Quadro 10 — Índices Zootécnicos (input)
    num_animais = models.PositiveIntegerField(
        verbose_name="Número de Animais",
        help_text="Cópia editável de Lote.num_animais — não sincronizada.",
    )
    gmd_esperado_kg = models.FloatField(
        verbose_name="GMD (kg) esperado",
        help_text="Cópia editável de Lote.gmd_esperado — não sincronizada.",
    )
    estimativa_permanencia_dias = models.PositiveIntegerField(
        verbose_name="Estimativa de permanência (dias)",
    )
    peso_entrada_kg = models.FloatField(
        verbose_name="Peso Vivo Real (Kg) na Entrada",
        help_text="Cópia editável de Lote.peso_vivo — não sincronizada.",
    )
    cms_percentual_pv = models.FloatField(
        verbose_name="CMS (%) do peso vivo",
        help_text=(
            "Fração 0-1 (ex.: 0.0297 = 2,97%). NÃO é ExigenciaConfigurada."
            "cms_kg — é uma estimativa simplificada só para projeção de "
            "consumo/custo ao longo do período de confinamento."
        ),
    )
    perdas_alimentos_percentual = models.FloatField(
        default=0.08,
        verbose_name="Perdas de Alimentos (%)",
        help_text="Fração 0-1 (ex.: 0.08 = 8%). Sobra/desperdício no cocho.",
    )

    # Quadro 13 — Valor (R$) obtido pelo Kg de PV
    preco_venda_kg_pv = models.FloatField(
        null=True, blank=True,
        verbose_name="Preço de venda (R$/kg de PV)",
        help_text="Preço esperado de venda do animal vivo, por kg de peso vivo.",
    )

    dt_criacao = models.DateTimeField(auto_now_add=True)
    dt_alteracao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Parâmetros de Viabilidade"
        verbose_name_plural = "Parâmetros de Viabilidade"

    def __str__(self):
        return f"Viabilidade — Formulação #{self.formulacao_id}"
