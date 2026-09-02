from unittest.mock import patch

from rest_framework import serializers

from formulacao.api.serializers import (
    AtualizarPercentualVolumosoInputSerializer,
    FormulacaoDetailSerializer,
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


def test_geracao_inicial_preserva_fracao_ja_aceita():
    serializer = GerarFormulacaoInicialInputSerializer(
        data={"percentual_alvo_volumoso": 0.5}
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["percentual_alvo_volumoso"] == 0.5


def test_geracao_inicial_normaliza_vinte_por_cento_para_fracao():
    serializer = GerarFormulacaoInicialInputSerializer(
        data={"percentual_alvo_volumoso": 20}
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["percentual_alvo_volumoso"] == 0.20
    assert serializer.validated_data["modo_percentual_volumoso"] == (
        "FIXADO_PELO_USUARIO"
    )


def test_modo_automatico_rejeita_percentual_conflitante():
    serializer = GerarFormulacaoInicialInputSerializer(data={
        "modo_percentual_volumoso": "OTIMIZADO_PELO_SISTEMA",
        "percentual_alvo_volumoso": 20,
    })

    assert not serializer.is_valid()
    assert "percentual_alvo_volumoso" in serializer.errors


def test_atualizacao_permite_liberar_percentual_fixo():
    serializer = AtualizarPercentualVolumosoInputSerializer(data={
        "modo_percentual_volumoso": "OTIMIZADO_PELO_SISTEMA",
    })

    assert serializer.is_valid(), serializer.errors
    assert "percentual_alvo_volumoso" not in serializer.validated_data


def test_saida_da_formulacao_expoe_alvo_de_volumoso_em_percentual():
    serializer = FormulacaoListSerializer()

    with patch.object(
        serializers.ModelSerializer,
        "to_representation",
        return_value={
            "modo_percentual_volumoso": "OTIMIZADO_PELO_SISTEMA",
            "percentual_alvo_volumoso": None,
            "percentual_volumoso_aplicado": 0.0,
            "origem_percentual_volumoso": "SISTEMA",
        },
    ):
        data = serializer.to_representation(object())

    assert data["percentual_alvo_volumoso"] is None
    assert data["percentual_volumoso_aplicado"] == 0.0
    assert data["modo_percentual_volumoso"] == "OTIMIZADO_PELO_SISTEMA"
    assert data["origem_percentual_volumoso"] == "SISTEMA"


def test_serializers_documentam_contrato_dos_dois_modos_no_schema():
    entrada_geracao = GerarFormulacaoInicialInputSerializer().fields
    entrada_atualizacao = AtualizarPercentualVolumosoInputSerializer().fields
    saida = FormulacaoDetailSerializer().fields

    for campos in (entrada_geracao, entrada_atualizacao):
        assert "modo_percentual_volumoso" in campos
        assert "percentual_alvo_volumoso" in campos
    assert "modo_percentual_volumoso" in saida
    assert "percentual_volumoso_aplicado" in saida
    assert "origem_percentual_volumoso" in saida
    assert "adequacao_nutricional_completa" in saida
    assert "desvios_nutricionais" in saida
