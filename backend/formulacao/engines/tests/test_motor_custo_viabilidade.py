"""Testes numéricos dos motores de custo e de projeção econômica."""

import numpy as np
import pytest

from formulacao.engines.motor_custo import EntradaCusto, MotorCusto
from formulacao.engines.motor_viabilidade import MotorViabilidade, ParametrosViabilidade


def test_motor_custo_ignora_preco_ausente_de_ingrediente_sem_participacao():
    """Um item zerado na dieta não deve produzir um falso alerta de preço."""
    saida = MotorCusto.calcular(EntradaCusto(
        fracoes_ms=np.array([1.0, 0.0]),
        custos_kg_mn=np.array([2.0, 0.0]),
        ms_percentuais=np.array([50.0, 80.0]),
        cms_total_kg=1.0,
        num_animais=10,
    ))

    assert saida.custo_animal_dia == pytest.approx(4.0)
    assert saida.custo_lote_dia == pytest.approx(40.0)
    assert saida.tem_ingrediente_sem_preco is False


def test_motor_viabilidade_preserva_unidade_de_materia_natural():
    """A conversão MS para MN não pode reduzir consumo e custos em dez vezes."""
    parametros = ParametrosViabilidade(
        num_animais=10,
        gmd_esperado_kg=0.2,
        estimativa_permanencia_dias=10,
        peso_entrada_kg=20.0,
        cms_percentual_pv=0.03,
        perdas_alimentos_percentual=0.10,
        preco_venda_kg_pv=10.0,
    )

    saida = MotorViabilidade.calcular(
        parametros=parametros,
        fracoes_ms=np.array([1.0]),
        ms_percentuais=np.array([50.0]),
        precos_kg_mn=np.array([2.0]),
        nomes=['Silagem'],
        ingrediente_ids=[1],
    )

    assert saida.indices.cms_kg_dia == pytest.approx(0.63)
    assert saida.consumo_kg_dia_animal_total == pytest.approx(1.386)
    assert saida.kg_total_periodo_total == pytest.approx(138.6)
    assert saida.investimento_total_geral == pytest.approx(277.2)
    assert saida.custo_por_animal_total == pytest.approx(27.72)


def test_motor_viabilidade_rejeita_vetores_desalinhados():
    """Dados de ingredientes em ordens ou tamanhos diferentes não são calculados."""
    parametros = ParametrosViabilidade(1, 0.2, 10, 20.0, 0.03, 0.1, 10.0)

    with pytest.raises(ValueError, match='mesmo tamanho'):
        MotorViabilidade.calcular(
            parametros,
            np.array([1.0]),
            np.array([50.0, 80.0]),
            np.array([2.0]),
            ['Silagem'],
            [1],
        )


def test_motor_viabilidade_calcula_indices_e_custos_sem_quadros_economicos():
    """Quadros 10 e 11 não dependem do preço de venda de peso vivo."""
    parametros = ParametrosViabilidade(1, 0.2, 10, 20.0, 0.03, 0.1, None)

    saida = MotorViabilidade.calcular(
        parametros,
        np.array([1.0]),
        np.array([50.0]),
        np.array([2.0]),
        ["Silagem"],
        [1],
    )

    assert saida.indices.cms_kg_dia == pytest.approx(0.63)
    assert len(saida.linhas_custo) == 1
    assert saida.preco_minimo_kg_pv is None
    assert saida.resultado_animal is None
    assert saida.resultado_lote is None
