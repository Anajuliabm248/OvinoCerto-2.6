from django.db import migrations


VALORES_NRC = {
    "pv_percentual": 3.58,
    "cms_kg": 1.074,
    "pb_g": 151.0,
    "pb_percentual": 14.02,
    "ndt_kg": 0.850,
    "ndt_percentual": 79.14,
    "fdn_kg": 0.322,
    "fdn_percentual": 30.0,
    "ee_kg": 0.075,
    "ee_percentual": 7.0,
    "ca_g": 4.5,
    "ca_percentual": 0.42,
    "p_g": 3.2,
    "p_percentual": 0.30,
    "ca_p_percentual": 1.41,
}

CONFIGURACOES = {
    "PB": (">=", 14.02, None),
    "NDT": (">=", 79.14, None),
    "FDN": (">=", 30.0, None),
    "EE": ("<=", None, 7.0),
    "CA": (">=", 0.42, None),
    "P": (">=", 0.30, None),
    "CA_P": (">=", 1.41, None),
}


def corrigir_referencia_id11(apps, schema_editor):
    ExigenciaNRC = apps.get_model("exigencia_nrc", "ExigenciaNRC")
    ExigenciaConfigurada = apps.get_model("formulacao", "ExigenciaConfigurada")
    ConfiguracaoNutriente = apps.get_model("formulacao", "ConfiguracaoNutriente")

    referencias = ExigenciaNRC.objects.filter(
        categoria="cordeiros_4_meses",
        fase="crescimento",
        pv_kg=30.0,
        gmd_kg=0.25,
    )

    for referencia in referencias:
        for campo, valor in VALORES_NRC.items():
            setattr(referencia, campo, valor)
        referencia.save(update_fields=list(VALORES_NRC))

        exigencias = ExigenciaConfigurada.objects.filter(
            exigencia_nrc_origem_id=referencia.id
        )
        exigencias.update(cms_kg=VALORES_NRC["cms_kg"])

        for nutriente, (operador, valor_min, valor_max) in CONFIGURACOES.items():
            ConfiguracaoNutriente.objects.filter(
                exigencia_configurada__in=exigencias,
                nutriente=nutriente,
                alterado_pelo_usuario=False,
            ).update(
                operador=operador,
                valor_min=valor_min,
                valor_max=valor_max,
                valor_origem_nrc=(
                    valor_min if valor_min is not None else valor_max
                ),
            )


class Migration(migrations.Migration):
    dependencies = [
        ("exigencia_nrc", "0002_remove_exigencianrc_dias_fase"),
        ("formulacao", "0007_alter_ingredienteformulacao_origem_custo_and_more"),
    ]

    operations = [
        migrations.RunPython(
            corrigir_referencia_id11,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
