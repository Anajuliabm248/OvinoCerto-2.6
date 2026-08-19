from unittest.mock import patch

from rest_framework import serializers

from formulacao.api.serializers import IngredienteFormulacaoSerializer


def test_participacao_residual_e_exposta_como_zero_numerico():
    serializer = IngredienteFormulacaoSerializer()

    with patch.object(
        serializers.ModelSerializer,
        "to_representation",
        return_value={"ms_porcent": 2.0698495689799002e-14},
    ):
        data = serializer.to_representation(object())

    assert data["ms_porcent"] == 0.0
    assert isinstance(data["ms_porcent"], float)


def test_participacao_real_pequena_nao_e_zerada_na_saida():
    serializer = IngredienteFormulacaoSerializer()

    with patch.object(
        serializers.ModelSerializer,
        "to_representation",
        return_value={"ms_porcent": 0.000001},
    ):
        data = serializer.to_representation(object())

    assert data["ms_porcent"] == 0.000001
