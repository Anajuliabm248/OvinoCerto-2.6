from django.db import migrations, models


def preencher_estado_volumoso(apps, schema_editor):
    from django.db.models import Sum

    Formulacao = apps.get_model("formulacao", "Formulacao")
    IngredienteFormulacao = apps.get_model("formulacao", "IngredienteFormulacao")

    for formulacao in Formulacao.objects.all().iterator():
        alvo = formulacao.percentual_alvo_volumoso
        aplicado = (
            IngredienteFormulacao.objects
            .filter(
                formulacao_id=formulacao.pk,
                ingrediente__classificacao__iexact="volumoso",
            )
            .aggregate(soma=Sum("ms_porcent"))["soma"]
        )
        if aplicado is None:
            aplicado = float(alvo if alvo is not None else 0.50) * 100.0

        Formulacao.objects.filter(pk=formulacao.pk).update(
            modo_percentual_volumoso="FIXADO_PELO_USUARIO",
            percentual_volumoso_aplicado=max(0.0, min(1.0, float(aplicado) / 100.0)),
            origem_percentual_volumoso="USUARIO",
        )


def restaurar_alvo_legado(apps, schema_editor):
    Formulacao = apps.get_model("formulacao", "Formulacao")
    for formulacao in Formulacao.objects.filter(
        percentual_alvo_volumoso__isnull=True
    ).iterator():
        Formulacao.objects.filter(pk=formulacao.pk).update(
            percentual_alvo_volumoso=formulacao.percentual_volumoso_aplicado
        )


class Migration(migrations.Migration):

    dependencies = [
        ("formulacao", "0010_alter_eventoformulacao_tipo_evento"),
    ]

    operations = [
        migrations.AlterField(
            model_name="formulacao",
            name="percentual_alvo_volumoso",
            field=models.FloatField(
                blank=True,
                default=0.50,
                help_text=(
                    "Fonte de verdade do alvo rigido somente quando o modo e "
                    "FIXADO_PELO_USUARIO. Armazenado como fracao de 0 a 1; fica "
                    "nulo no modo OTIMIZADO_PELO_SISTEMA."
                ),
                null=True,
                verbose_name="Alvo de volumosos (fração da MS)",
            ),
        ),
        migrations.AddField(
            model_name="formulacao",
            name="modo_percentual_volumoso",
            field=models.CharField(
                choices=[
                    ("FIXADO_PELO_USUARIO", "Fixado pelo usuario"),
                    ("OTIMIZADO_PELO_SISTEMA", "Otimizado pelo sistema"),
                ],
                default="FIXADO_PELO_USUARIO",
                help_text=(
                    "Controla o motor: no modo fixado, percentual_alvo_volumoso e "
                    "restricao rigida; no automatico, o total de volumoso e resultado."
                ),
                max_length=30,
                verbose_name="Modo de definição do volumoso",
            ),
        ),
        migrations.AddField(
            model_name="formulacao",
            name="origem_percentual_volumoso",
            field=models.CharField(
                choices=[("USUARIO", "Usuario"), ("SISTEMA", "Sistema")],
                default="USUARIO",
                max_length=10,
                verbose_name="Origem do percentual de volumoso",
            ),
        ),
        migrations.AddField(
            model_name="formulacao",
            name="percentual_volumoso_aplicado",
            field=models.FloatField(
                default=0.50,
                help_text=(
                    "Resultado auditavel entre 0 e 1, calculado a partir das "
                    "participacoes persistidas; nunca configura o motor."
                ),
                verbose_name="Volumoso efetivamente aplicado (fração da MS)",
            ),
        ),
        migrations.RunPython(preencher_estado_volumoso, restaurar_alvo_legado),
        migrations.AddConstraint(
            model_name="formulacao",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        modo_percentual_volumoso="FIXADO_PELO_USUARIO",
                        percentual_alvo_volumoso__isnull=False,
                        origem_percentual_volumoso="USUARIO",
                    )
                    | models.Q(
                        modo_percentual_volumoso="OTIMIZADO_PELO_SISTEMA",
                        percentual_alvo_volumoso__isnull=True,
                        origem_percentual_volumoso="SISTEMA",
                    )
                ),
                name="formulacao_estado_volumoso_coerente",
            ),
        ),
        migrations.AddConstraint(
            model_name="formulacao",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(percentual_alvo_volumoso__isnull=True)
                    | models.Q(
                        percentual_alvo_volumoso__gte=0.0,
                        percentual_alvo_volumoso__lte=1.0,
                    )
                ),
                name="formulacao_alvo_volumoso_0_1",
            ),
        ),
        migrations.AddConstraint(
            model_name="formulacao",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    percentual_volumoso_aplicado__gte=0.0,
                    percentual_volumoso_aplicado__lte=1.0,
                ),
                name="formulacao_aplicado_volumoso_0_1",
            ),
        ),
    ]
