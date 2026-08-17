"""Referências zootécnicas validadas usadas como guia da geração inicial.

As receitas deste modelo não são regras do otimizador. Elas registram casos
publicados, com a sua versão e composição, para que o motor possa reconhecer
um cenário equivalente ou usar um caso próximo como âncora de baixa confiança.
"""

from django.db import models


class ReferenciaSuplementoValidada(models.Model):
    """Um suplemento concentrado validado, importado de uma fonte rastreável."""

    codigo = models.CharField(max_length=40, unique=True, db_index=True)
    fonte = models.CharField(max_length=200)
    versao_fonte = models.CharField(max_length=40, default="v1")
    origem_arquivo = models.CharField(max_length=255)
    categoria_id_origem = models.CharField(max_length=40)
    categoria = models.CharField(max_length=40, db_index=True)
    fase = models.CharField(max_length=40, db_index=True)
    fase_meses = models.PositiveSmallIntegerField(null=True, blank=True)
    peso_vivo_kg = models.FloatField()
    gmd_kg = models.FloatField()
    cms_kg = models.FloatField()

    # Exigências da linha NRC que identifica o cenário.
    pb_requisito_pct = models.FloatField()
    ndt_requisito_pct = models.FloatField()
    ca_requisito_pct = models.FloatField()
    p_requisito_pct = models.FloatField()
    ca_p_requisito = models.FloatField()

    # Resultado publicado, preservado para auditoria da importação.
    pb_resultado_pct = models.FloatField()
    ndt_resultado_pct = models.FloatField()
    fdn_resultado_pct = models.FloatField()
    ee_resultado_pct = models.FloatField()
    ca_resultado_pct = models.FloatField()
    p_resultado_pct = models.FloatField()
    ca_p_resultado = models.FloatField()
    dieta_ms_pct = models.FloatField()
    ativo = models.BooleanField(default=True, db_index=True)
    dt_criacao = models.DateTimeField(auto_now_add=True)
    dt_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Referência de suplemento validada"
        verbose_name_plural = "Referências de suplementos validadas"
        ordering = ["categoria", "fase", "peso_vivo_kg", "gmd_kg", "codigo"]
        indexes = [
            models.Index(
                fields=["ativo", "categoria", "fase"],
                name="formulacao__ativo_36b49c_idx",
            ),
        ]

    def __str__(self):
        return f"{self.codigo} — {self.categoria}/{self.fase}"


class ReferenciaSuplementoIngrediente(models.Model):
    """Componente e assinatura bromatológica de uma referência validada."""

    referencia = models.ForeignKey(
        ReferenciaSuplementoValidada,
        on_delete=models.CASCADE,
        related_name="ingredientes",
    )
    codigo_origem = models.CharField(max_length=80)
    nome_origem = models.CharField(max_length=200)
    classificacao = models.CharField(max_length=30)
    tipo = models.CharField(max_length=40)
    participacao_pct_ms = models.FloatField()
    ms_pct = models.FloatField()
    pb_pct = models.FloatField()
    ndt_pct = models.FloatField()
    fdn_pct = models.FloatField()
    ee_pct = models.FloatField()
    ca_pct = models.FloatField()
    p_pct = models.FloatField()

    class Meta:
        verbose_name = "Ingrediente da referência validada"
        verbose_name_plural = "Ingredientes das referências validadas"
        ordering = ["referencia", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["referencia", "codigo_origem"],
                name="referencia_suplemento_codigo_origem_unico",
            ),
        ]

    def __str__(self):
        return f"{self.referencia.codigo}: {self.nome_origem}"
