"""Testes das combinações e quantidades aceitas em um lote."""

import pytest
from rest_framework import serializers

from lote.serializers import LoteSerializer


def test_lote_rejeita_valores_zootecnicos_negativos():
    """Peso, GMD e número de animais inválidos são informados juntos ao cliente."""
    serializer = LoteSerializer()
    dados = {
        'categoria': 'cordeiros_4_meses',
        'fase': 'crescimento',
        'peso_vivo': 0,
        'gmd_esperado': -0.1,
        'num_animais': 0,
    }

    with pytest.raises(serializers.ValidationError) as erro:
        serializer.validate(dados)

    assert 'peso_vivo' in erro.value.detail
    assert 'gmd_esperado' in erro.value.detail
    assert 'num_animais' in erro.value.detail
