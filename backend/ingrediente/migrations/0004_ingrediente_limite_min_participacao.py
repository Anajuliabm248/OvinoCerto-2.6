from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ingrediente", "0003_historicoprecoingrediente_precoingredienteusuario"),
    ]

    operations = [
        migrations.AddField(
            model_name="ingrediente",
            name="limite_min_participacao",
            field=models.FloatField(
                blank=True,
                help_text=(
                    "Percentual mínimo (0-100) na matéria seca total. Use apenas "
                    "quando houver justificativa técnica para a inclusão do ingrediente."
                ),
                null=True,
                verbose_name="Limite mínimo de participação (% MS)",
            ),
        ),
    ]
