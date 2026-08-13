"""Representação HTTP das referências nutricionais publicadas pelo NRC."""

from rest_framework import serializers
from lote.models import FASES_COM_PARTO_E_DIAS, FASES_VALIDAS
from .models import ExigenciaNRC

# pylint: disable= too-few-public-methods

class ExigenciaNRCSerializer(serializers.ModelSerializer):
    """Entrega valores técnicos junto dos rótulos legíveis de categoria e fase."""
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
        """Expõe a tabela de referência sem permitir alteração do identificador."""
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

    def validate(self, attrs):
        """Evita que administradores incluam linhas NRC com unidades incoerentes."""
        instance = getattr(self, 'instance', None)
        categoria = attrs.get('categoria', getattr(instance, 'categoria', None))
        fase = attrs.get('fase', getattr(instance, 'fase', None))
        tipo_parto = attrs.get('tipo_parto', getattr(instance, 'tipo_parto', None))

        if categoria and fase and fase not in FASES_VALIDAS.get(categoria, []):
            raise serializers.ValidationError({
                'fase': 'Esta fase produtiva não pertence à categoria informada.'
            })
        if fase in FASES_COM_PARTO_E_DIAS and not tipo_parto:
            raise serializers.ValidationError({
                'tipo_parto': 'Informe o tipo de parto para gestação ou lactação.'
            })

        erros = {}
        for campo, valor in attrs.items():
            if campo == 'pv_kg' and valor <= 0:
                erros[campo] = 'O peso vivo deve ser maior que zero.'
            elif campo in {
                'pv_nascer_kg', 'producao_leite_kg_dia', 'gmd_kg', 'pv_percentual',
                'cms_kg', 'pb_g', 'pb_percentual', 'ndt_kg', 'ndt_percentual',
                'fdn_kg', 'fdn_percentual', 'ee_kg', 'ee_percentual', 'ca_g',
                'ca_percentual', 'p_g', 'p_percentual', 'ca_p_percentual',
            } and valor is not None and valor < 0:
                erros[campo] = 'O valor não pode ser negativo.'
        if erros:
            raise serializers.ValidationError(erros)
        return attrs
