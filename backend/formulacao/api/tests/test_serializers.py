from unittest.mock import patch

from rest_framework import serializers

from formulacao.api.serializers import (
    AtualizarPercentualVolumosoInputSerializer,
    FormulacaoListSerializer,
    GerarFormulacaoInicialInputSerializer,
    IngredienteFormulacaoSerializer,
)


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


def test_alvo_de_volumoso_da_api_e_normalizado_de_percentual_para_fracao():
    serializer = AtualizarPercentualVolumosoInputSerializer(
        data={"percentual_alvo_volumoso": 50.0}
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["percentual_alvo_volumoso"] == 0.5


def test_geracao_inicial_interpreta_meio_por_cento_como_percentual():
    serializer = GerarFormulacaoInicialInputSerializer(
        data={"percentual_alvo_volumoso": 0.5}
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["percentual_alvo_volumoso"] == 0.005


def test_saida_da_formulacao_expoe_alvo_de_volumoso_em_percentual():
    serializer = FormulacaoListSerializer()

    with patch.object(
        serializers.ModelSerializer,
        "to_representation",
        return_value={"percentual_alvo_volumoso": 0.5},
    ):
        data = serializer.to_representation(object())

    assert data["percentual_alvo_volumoso"] == 50.0
