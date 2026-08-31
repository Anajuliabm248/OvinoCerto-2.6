from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("formulacao", "0013_pb_padrao_como_valor_ideal"),
    ]

    operations = [
        migrations.AddField(
            model_name="formulacao",
            name="quantidade_mistura_mn_kg",
            field=models.FloatField(
                blank=True,
                help_text=(
                    "Quantidade persistida de matéria natural da mistura "
                    "concentrada a preparar. Deve ser maior que zero quando "
                    "informada."
                ),
                null=True,
                verbose_name="Quantidade da mistura concentrada (kg MN)",
            ),
        ),
        migrations.AddConstraint(
            model_name="formulacao",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(quantidade_mistura_mn_kg__isnull=True)
                    | models.Q(quantidade_mistura_mn_kg__gt=0.0)
                ),
                name="formulacao_quantidade_mistura_mn_positiva",
            ),
        ),
    ]
