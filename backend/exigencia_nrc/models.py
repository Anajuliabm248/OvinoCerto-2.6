"""Tabela de referência nutricional usada como ponto de partida das dietas."""

from django.db import models

from lote.models import (
    CATEGORIA_CHOICES,
    FASE_CHOICES,
    TIPO_PARTO_CHOICES
)

# pylint: disable=too-few-public-methods, no-member

class ExigenciaNRC(models.Model):
    """
    Tabela de exigências nutricionais segundo NRC (2007).
    Usada como referência para formulação de dietas.
    """
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        verbose_name='Categoria',
        db_index=True,
    )
    fase = models.CharField(
        max_length=20,
        choices=FASE_CHOICES,
        verbose_name='Fase produtiva',
        db_index=True,
    )
    pv_kg = models.FloatField(verbose_name='Peso vivo (kg)', db_index=True)
    tipo_parto = models.PositiveSmallIntegerField(
        choices=TIPO_PARTO_CHOICES,
        blank=True, null=True,
        verbose_name='Tipo de parto',
        help_text='Requerido para fases de gestação e lactação.',
    )
    pv_nascer_kg = models.FloatField(
        blank=True, null=True,
        verbose_name='PV ao nascer (kg)',
    )
    producao_leite_kg_dia = models.FloatField(
        blank=True, null=True,
        verbose_name='Produção de leite (kg/dia)',
    )
    gmd_kg = models.FloatField(
        blank=True, null=True,
        verbose_name='GMD (kg/dia)',
        db_index=True,
    )
    pv_percentual = models.FloatField(
        blank=True, null=True,
        verbose_name='% PV',
    )
    cms_kg = models.FloatField(
        blank=True, null=True,
        verbose_name='CMS (kg/dia)',
    )
    pb_g = models.FloatField(
        blank=True, null=True,
        verbose_name='PB (g)',
    )
    pb_percentual = models.FloatField(
        blank=True, null=True,
        verbose_name='PB (%)',
    )
    ndt_kg = models.FloatField(
        blank=True, null=True,
        verbose_name='NDT (kg)',
    )
    ndt_percentual = models.FloatField(
        blank=True, null=True,
        verbose_name='NDT (%)',
    )
    fdn_kg = models.FloatField(
        blank=True, null=True,
        verbose_name='FDN (kg)',
    )
    fdn_percentual = models.FloatField(
        blank=True, null=True,
        verbose_name='FDN (%)',
    )
    ee_kg = models.FloatField(
        blank=True, null=True,
        verbose_name='EE (kg)',
    )
    ee_percentual = models.FloatField(
        blank=True, null=True,
        verbose_name='EE (%)',
    )
    ca_g = models.FloatField(
        blank=True, null=True,
        verbose_name='Ca (g)',
    )
    ca_percentual = models.FloatField(
        blank=True, null=True,
        verbose_name='Ca (%)',
    )
    p_g = models.FloatField(
        blank=True, null=True,
        verbose_name='P (g)',
    )
    p_percentual = models.FloatField(
        blank=True, null=True,
        verbose_name='P (%)',
    )
    ca_p_percentual = models.FloatField(
        blank=True, null=True,
        verbose_name='Relação Ca:P',
    )

    class Meta:
        """Ordena e indexa as colunas mais usadas na escolha da exigência."""
        verbose_name = 'Exigência Nutricional (NRC)'
        verbose_name_plural = 'Exigências Nutricionais (NRC)'
        ordering = ['categoria', 'fase', 'pv_kg', 'gmd_kg']
        indexes = [
            models.Index(fields=['categoria', 'fase', 'pv_kg']),
        ]

    def __str__(self):
        """Resume categoria, fase, peso e ganho diário da linha NRC."""
        gmd_str = f' GMD={self.gmd_kg}' if self.gmd_kg else ''
        return f'{self.get_categoria_display()} | {self.get_fase_display()} \
            | PV={self.pv_kg}kg{gmd_str}'
