from rest_framework import serializers
from .models import ExigenciaNRC


class ExigenciaNRCSerializer(serializers.ModelSerializer):
    categoria_display = serializers.CharField(
        source='get_categoria_display', read_only=True
    )
    fase_display = serializers.CharField(
        source='get_fase_display', read_only=True
    )
    tipo_parto_display = serializers.CharField(
        source='get_tipo_parto_display', read_only=True
    )

    class Meta:
        model = ExigenciaNRC
        fields = [
            'id',
            'categoria',
            'categoria_display',
            'fase',
            'fase_display',
            'pv_kg',
            'tipo_parto',
            'tipo_parto_display',
            'dias_fase',
            'pv_nascer_kg',
            'producao_leite_kg_dia',
            'gmd_kg',
            'pv_percentual',
            'cms_kg',
            'pb_g',
            'pb_percentual',
            'ndt_kg',
            'ndt_percentual',
            'fdn_kg',
            'fdn_percentual',
            'ee_kg',
            'ee_percentual',
            'ca_g',
            'ca_percentual',
            'p_g',
            'p_percentual',
            'ca_p_percentual',
        ]
        read_only_fields = ['id']