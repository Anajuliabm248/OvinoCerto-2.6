from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ingrediente", "0004_ingrediente_limite_min_participacao"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ingrediente",
            name="limite_min_participacao",
            field=models.FloatField(
                blank=True,
                help_text=(
                    "Percentual mínimo (0-100) na matéria seca total. Use apenas "
                    "quando houver justificativa técnica para a inclusão do ingrediente. "
                    "Para dose fixa, informe o mesmo valor no limite máximo."
                ),
                null=True,
                verbose_name="Limite mínimo de participação (% MS)",
            ),
        ),
        migrations.AlterField(
            model_name="ingrediente",
            name="limite_max_participacao",
            field=models.FloatField(
                blank=True,
                help_text=(
                    "Percentual máximo (0-100) que este ingrediente pode representar "
                    "na matéria seca total de uma formulação (ex.: bicarbonato de sódio "
                    "limitado a 1.5%). Use o mesmo valor do limite mínimo para uma dose "
                    "fixa. Deixe em branco para não aplicar nenhum limite."
                ),
                null=True,
                verbose_name="Limite máximo de participação (% MS)",
            ),
        ),
    ]
