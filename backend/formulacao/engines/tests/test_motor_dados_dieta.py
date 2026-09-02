"""Invariantes quantitativos do motor puro de Dados da Dieta."""

# pylint: disable=missing-function-docstring, too-many-arguments

import math

import pytest

from formulacao.engines.motor_dados_dieta import (
    EntradaDadosDieta,
    LinhaDadosDietaEntrada,
    MotorDadosDieta,
)


def _linha(
    identificador,
    classificacao,
    participacao,
    ms_kg,
    mn_kg,
    *,
    ms_ingrediente=50.0,
):
    return LinhaDadosDietaEntrada(
        ing_form_id=identificador,
        ingrediente_id=identificador,
        classificacao=classificacao,
        tipo="silagens" if classificacao == "volumoso" else "energetico",
        nome=f"Ingrediente {identificador}",
        ms_percentual_ingrediente=ms_ingrediente,
        ms_kg_dia=ms_kg,
        mn_kg_dia=mn_kg,
        participacao_ms_percentual=participacao,
        preco_kg_mn=2.0,
        custo_dia=mn_kg * 2.0,
        origem_custo="CATALOGO",
    )


def _mista(quantidade=None):
    return MotorDadosDieta.calcular(EntradaDadosDieta(
        linhas=(
            _linha(1, "volumoso", 50.0, 1.0, 2.0),
            _linha(2, "concentrado", 30.0, 0.6, 0.75, ms_ingrediente=80.0),
            _linha(3, "concentrado", 20.0, 0.4, 0.5, ms_ingrediente=80.0),
        ),
        quantidade_mistura_mn_kg=quantidade,
    ))


def test_dieta_com_volumoso_e_concentrado_fecha_todos_os_totais():
    saida = _mista()

    assert saida.totais_dieta["participacao_ms_percentual"] == 100.0
    assert saida.totais_dieta["participacao_mn_percentual"] == 100.0
    assert saida.resumo_por_classificacao["volumoso"]["ms_kg_total"] == 1.0
    assert saida.resumo_por_classificacao["concentrado"]["ms_kg_total"] == 1.0
    assert saida.mistura_concentrada["disponivel"] is True
    assert saida.mistura_concentrada["totais"] == {
        "participacao_ms_mistura_percentual": 100.0,
        "mn_kg_por_100kg_mistura": 100.0,
        "mn_kg_para_quantidade": None,
    }


def test_dieta_somente_com_concentrados_mantem_resumo_do_volumoso_zerado():
    saida = MotorDadosDieta.calcular(EntradaDadosDieta(linhas=(
        _linha(1, "concentrado", 60.0, 0.6, 0.75, ms_ingrediente=80.0),
        _linha(2, "concentrado", 40.0, 0.4, 0.5, ms_ingrediente=80.0),
    )))

    assert saida.resumo_por_classificacao["volumoso"] == {
        "mn_kg_total": 0,
        "ms_kg_total": 0,
        "participacao_ms_percentual": 0,
        "participacao_mn_percentual": 0.0,
    }
    assert saida.mistura_concentrada["disponivel"] is True


def test_dieta_somente_com_volumosos_indisponibiliza_apenas_a_mistura():
    saida = MotorDadosDieta.calcular(EntradaDadosDieta(linhas=(
        _linha(1, "volumoso", 100.0, 1.0, 2.0),
    )))

    mistura = saida.mistura_concentrada
    assert mistura["disponivel"] is False
    assert mistura["motivo_indisponibilidade"] == (
        "SEM_CONCENTRADO_COM_PARTICIPACAO_POSITIVA"
    )
    assert mistura["linhas"] == []
    assert saida.totais_dieta["participacao_mn_percentual"] == 100.0


def test_concentrado_selecionado_com_zero_permanece_na_resposta():
    saida = MotorDadosDieta.calcular(EntradaDadosDieta(
        linhas=(
            _linha(1, "volumoso", 100.0, 1.0, 2.0),
            _linha(2, "concentrado", 0.0, 0.0, 0.0, ms_ingrediente=0.0),
        ),
        quantidade_mistura_mn_kg=300.0,
    ))

    assert saida.mistura_concentrada["disponivel"] is False
    assert saida.mistura_concentrada["linhas"] == [{
        "ing_form_id": 2,
        "ingrediente_id": 2,
        "nome": "Ingrediente 2",
        "participacao_ms_mistura_percentual": 0.0,
        "mn_kg_por_100kg_mistura": 0.0,
        "mn_kg_para_quantidade": 0.0,
    }]


def test_ingrediente_positivo_com_ms_invalida_expoe_id_e_nome():
    with pytest.raises(ValueError, match=r"Ingrediente 1 \(Ingrediente 1\).*MS inválida"):
        MotorDadosDieta.calcular(EntradaDadosDieta(linhas=(
            _linha(1, "concentrado", 100.0, 1.0, 0.0, ms_ingrediente=0.0),
        )))


def test_quantidade_ausente_nao_inventa_valores_da_coluna_x():
    saida = _mista()

    assert all(
        linha["mn_kg_para_quantidade"] is None
        for linha in saida.mistura_concentrada["linhas"]
    )
    assert saida.mistura_concentrada["totais"]["mn_kg_para_quantidade"] is None


def test_quantidade_300_fecha_exatamente_300_kg_mn():
    saida = _mista(300.0)

    assert saida.mistura_concentrada["totais"]["mn_kg_para_quantidade"] == 300.0
    assert sum(
        linha["mn_kg_para_quantidade"]
        for linha in saida.mistura_concentrada["linhas"]
    ) == 300.0


def test_quantidade_4200_fecha_exatamente_4200_kg_mn():
    saida = _mista(4200.0)

    assert saida.mistura_concentrada["totais"]["mn_kg_para_quantidade"] == 4200.0
    assert sum(
        linha["mn_kg_para_quantidade"]
        for linha in saida.mistura_concentrada["linhas"]
    ) == 4200.0


@pytest.mark.parametrize("quantidade", [0.0, -1.0, math.inf, -math.inf, math.nan])
def test_quantidade_invalida_e_rejeitada(quantidade):
    with pytest.raises(ValueError, match="finita e maior que zero"):
        _mista(quantidade)


def test_residuos_de_ponto_flutuante_sao_fechados_sem_nan_ou_negativos():
    saida = MotorDadosDieta.calcular(EntradaDadosDieta(
        linhas=(
            _linha(1, "volumoso", 33.3333333333333, 0.1, 0.3),
            _linha(2, "concentrado", 33.3333333333333, 0.1, 0.3),
            _linha(3, "concentrado", 33.3333333333334, 0.1, 0.3),
        ),
        quantidade_mistura_mn_kg=4200.0,
    ))

    numeros = []
    for linha in saida.linhas_dieta:
        numeros.extend([
            linha["participacao_ms_percentual"],
            linha["participacao_mn_percentual"],
            linha["ms_kg_dia"],
            linha["mn_kg_dia"],
        ])
    for linha in saida.mistura_concentrada["linhas"]:
        numeros.extend([
            linha["participacao_ms_mistura_percentual"],
            linha["mn_kg_por_100kg_mistura"],
            linha["mn_kg_para_quantidade"],
        ])
    assert all(math.isfinite(valor) and valor >= 0 for valor in numeros)
    assert saida.totais_dieta["participacao_ms_percentual"] == 100.0
    assert saida.totais_dieta["participacao_mn_percentual"] == 100.0
    assert saida.mistura_concentrada["totais"] == {
        "participacao_ms_mistura_percentual": 100.0,
        "mn_kg_por_100kg_mistura": 100.0,
        "mn_kg_para_quantidade": 4200.0,
    }
