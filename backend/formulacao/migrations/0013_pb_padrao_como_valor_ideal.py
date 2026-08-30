from django.db import migrations
from django.db.models import F


def definir_pb_padrao_como_igual(apps, schema_editor):
    ConfiguracaoNutriente = apps.get_model(
        "formulacao", "ConfiguracaoNutriente"
    )
    ConfiguracaoNutriente.objects.filter(
        nutriente="PB",
        alterado_pelo_usuario=False,
        valor_origem_nrc__isnull=False,
    ).update(
        operador="=",
        valor_min=F("valor_origem_nrc"),
        valor_max=F("valor_origem_nrc"),
    )


def restaurar_pb_padrao_como_minimo(apps, schema_editor):
    ConfiguracaoNutriente = apps.get_model(
        "formulacao", "ConfiguracaoNutriente"
    )
    ConfiguracaoNutriente.objects.filter(
        nutriente="PB",
        alterado_pelo_usuario=False,
        valor_origem_nrc__isnull=False,
        operador="=",
    ).update(
        operador=">=",
        valor_min=F("valor_origem_nrc"),
        valor_max=None,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("formulacao", "0012_alter_parametrosviabilidade_cms_percentual_pv_and_more"),
    ]

    operations = [
        migrations.RunPython(
            definir_pb_padrao_como_igual,
            restaurar_pb_padrao_como_minimo,
        ),
    ]
