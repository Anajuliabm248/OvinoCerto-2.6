import numpy as np
import pytest

from formulacao.domain.nutrientes import N_NUTRIENTES, Nutriente, indice_de
from formulacao.domain.participacao import OrigemParticipacao, ParticipacaoVetor
from formulacao.domain.requisito import RequisitoNutriente
from formulacao.engines.estimador_referencia import ContextoZootecnico
from formulacao.engines.motor_adequacao import ConfiguracaoIngrediente, MotorAdequacao


def test_redistribuir_reiniciando_livres_respeita_travados_e_alvo_volumoso_total():
    participacao = ParticipacaoVetor(
        ids_ingredientes=(1, 2, 3),
        fracoes=np.array([0.20, 0.40, 0.40], dtype=float),
        origens=(
            OrigemParticipacao.MANUAL_TRAVADA,
            OrigemParticipacao.CALCULADA,
            OrigemParticipacao.CALCULADA,
        ),
    )
    configuracoes = [
        ConfiguracaoIngrediente(classificacao="CONCENTRADO"),
        ConfiguracaoIngrediente(classificacao="VOLUMOSO"),
        ConfiguracaoIngrediente(classificacao="CONCENTRADO"),
    ]

    resultado = MotorAdequacao.redistribuir(
        matriz_M=np.zeros((3, N_NUTRIENTES), dtype=float),
        requisitos={},
        participacao_atual=participacao,
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.75,
        reiniciar_livres=True,
    )

    assert resultado.convergiu
    assert resultado.fracoes[0] == pytest.approx(0.20)
    assert resultado.fracoes[1] == pytest.approx(0.75)
    assert resultado.fracoes[2] == pytest.approx(0.05)
    assert resultado.fracoes.sum() == pytest.approx(1.0)


def test_gerar_distribuicao_respeita_alvo_volumoso_e_limites():
    configuracoes = [
        ConfiguracaoIngrediente(classificacao="VOLUMOSO", limite_max=0.30),
        ConfiguracaoIngrediente(classificacao="VOLUMOSO", limite_max=0.30),
        ConfiguracaoIngrediente(classificacao="CONCENTRADO"),
    ]

    resultado = MotorAdequacao.gerar_distribuicao_inicial(
        matriz_M=np.zeros((3, N_NUTRIENTES), dtype=float),
        requisitos={},
        configuracoes=configuracoes,
        percentual_alvo_volumoso=20.0,
    )

    assert resultado.convergiu
    assert resultado.fracoes[:2].sum() == pytest.approx(0.20)
    assert resultado.fracoes.sum() == pytest.approx(1.0)
    assert all(resultado.fracoes[i] <= configuracoes[i].limite_max + 1e-9 for i in range(3))


def test_gerar_distribuicao_rejeita_soma_de_limites_insuficiente():
    configuracoes = [
        ConfiguracaoIngrediente(classificacao="VOLUMOSO", limite_max=0.30),
        ConfiguracaoIngrediente(classificacao="CONCENTRADO", limite_max=0.40),
    ]

    with pytest.raises(ValueError, match="Alvo de volumoso inviável"):
        MotorAdequacao.gerar_distribuicao_inicial(
            matriz_M=np.zeros((2, N_NUTRIENTES), dtype=float),
            requisitos={},
            configuracoes=configuracoes,
            percentual_alvo_volumoso=0.30,
        )


def test_geracao_inicial_usa_tipo_e_mantem_todos_os_selecionados():
    configuracoes = [
        ConfiguracaoIngrediente(classificacao="VOLUMOSO", tipo="SILAGENS"),
        ConfiguracaoIngrediente(classificacao="CONCENTRADO", tipo="ENERGETICO"),
        ConfiguracaoIngrediente(classificacao="CONCENTRADO", tipo="PROTEICO"),
        ConfiguracaoIngrediente(classificacao="CONCENTRADO", tipo="MINERAL"),
    ]

    resultado = MotorAdequacao.gerar_distribuicao_inicial(
        matriz_M=np.zeros((4, N_NUTRIENTES), dtype=float),
        requisitos={},
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.50,
    )

    assert resultado.fracoes.sum() == pytest.approx(1.0, abs=1e-10)
    assert resultado.fracoes[0] == pytest.approx(0.50, abs=1e-9)
    assert np.all(resultado.fracoes > 0.0)
    assert resultado.fracoes[1] > resultado.fracoes[2] > resultado.fracoes[3]


def test_dose_fixa_de_aditivo_usa_minimo_igual_ao_maximo():
    """Aditivo sem contribuição na matriz só tem dose determinável se fixada."""
    configuracoes = [
        ConfiguracaoIngrediente(classificacao="CONCENTRADO", tipo="ENERGETICO"),
        ConfiguracaoIngrediente(
            classificacao="CONCENTRADO",
            tipo="ADITIVOS",
            limite_min=0.01,
            limite_max=0.01,
        ),
        ConfiguracaoIngrediente(
            classificacao="CONCENTRADO",
            tipo="ADITIVOS",
            limite_min=0.005,
            limite_max=0.005,
        ),
    ]

    resultado = MotorAdequacao.gerar_distribuicao_inicial(
        matriz_M=np.zeros((3, N_NUTRIENTES), dtype=float),
        requisitos={},
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.0,
    )

    assert resultado.convergiu
    assert resultado.fracoes == pytest.approx([0.985, 0.01, 0.005])


def test_meta_nutricional_impossivel_nao_destabiliza_distribuicao():
    matriz = np.zeros((2, N_NUTRIENTES), dtype=float)
    matriz[:, indice_de(Nutriente.PB)] = [8.0, 50.0]
    configuracoes = [
        ConfiguracaoIngrediente(classificacao="CONCENTRADO", tipo="ENERGETICO"),
        ConfiguracaoIngrediente(classificacao="CONCENTRADO", tipo="PROTEICO"),
    ]
    requisitos = {
        Nutriente.PB: RequisitoNutriente.maior_igual(Nutriente.PB, 55.0),
    }

    resultado = MotorAdequacao.gerar_distribuicao_inicial(
        matriz_M=matriz,
        requisitos=requisitos,
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.0,
    )

    assert resultado.fracoes.sum() == pytest.approx(1.0, abs=1e-10)
    assert np.all(resultado.fracoes > 0.0)
    assert resultado.fracoes.max() < 0.90


def test_limite_maximo_permanece_rigido_mesmo_com_meta_nutricional():
    matriz = np.zeros((3, N_NUTRIENTES), dtype=float)
    matriz[:, indice_de(Nutriente.PB)] = [8.0, 280.0, 0.0]
    configuracoes = [
        ConfiguracaoIngrediente(classificacao="CONCENTRADO", tipo="ENERGETICO"),
        ConfiguracaoIngrediente(
            classificacao="CONCENTRADO",
            tipo="PROTEICO",
            limite_max=0.01,
        ),
        ConfiguracaoIngrediente(
            classificacao="CONCENTRADO",
            tipo="MINERAL",
            limite_max=0.05,
        ),
    ]

    resultado = MotorAdequacao.gerar_distribuicao_inicial(
        matriz_M=matriz,
        requisitos={
            Nutriente.PB: RequisitoNutriente.maior_igual(Nutriente.PB, 30.0),
        },
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.0,
    )

    assert resultado.fracoes.sum() == pytest.approx(1.0, abs=1e-10)
    assert resultado.fracoes[1] <= 0.01 + 1e-10
    assert resultado.fracoes[2] <= 0.05 + 1e-10


def test_redistribuicao_com_unico_livre_rejeita_excesso_do_limite():
    participacao = ParticipacaoVetor(
        ids_ingredientes=(1, 2),
        fracoes=np.array([0.95, 0.05], dtype=float),
        origens=(
            OrigemParticipacao.MANUAL_TRAVADA,
            OrigemParticipacao.CALCULADA,
        ),
    )

    with pytest.raises(ValueError, match="Soma alvo inviável"):
        MotorAdequacao.redistribuir(
            matriz_M=np.zeros((2, N_NUTRIENTES), dtype=float),
            requisitos={},
            participacao_atual=participacao,
            configuracoes=[
                ConfiguracaoIngrediente(classificacao="CONCENTRADO"),
                ConfiguracaoIngrediente(
                    classificacao="CONCENTRADO",
                    limite_max=0.01,
                ),
            ],
        )


def test_redistribuicao_ampla_fecha_cem_sem_limite_artificial_de_variacao():
    participacao = ParticipacaoVetor(
        ids_ingredientes=(1, 2, 3),
        fracoes=np.array([0.80, 0.10, 0.10], dtype=float),
        origens=(
            OrigemParticipacao.MANUAL_TRAVADA,
            OrigemParticipacao.CALCULADA,
            OrigemParticipacao.CALCULADA,
        ),
    )

    resultado = MotorAdequacao.redistribuir(
        matriz_M=np.zeros((3, N_NUTRIENTES), dtype=float),
        requisitos={},
        participacao_atual=participacao,
        configuracoes=[
            ConfiguracaoIngrediente(classificacao="CONCENTRADO"),
            ConfiguracaoIngrediente(classificacao="CONCENTRADO"),
            ConfiguracaoIngrediente(classificacao="CONCENTRADO"),
        ],
    )

    assert resultado.fracoes[0] == pytest.approx(0.80)
    assert resultado.fracoes[1:].sum() == pytest.approx(0.20)
    assert resultado.fracoes.sum() == pytest.approx(1.0, abs=1e-10)


def test_projecao_preserva_soma_e_limites_em_varios_vetores():
    rng = np.random.default_rng(20260812)

    for n_ingredientes in range(2, 12):
        for _ in range(20):
            limites_maximos = rng.uniform(0.05, 0.60, size=n_ingredientes)
            limites_maximos[0] = 1.0
            bounds = [(0.0, float(limite)) for limite in limites_maximos]
            candidato = rng.normal(0.20, 0.50, size=n_ingredientes)

            resultado = MotorAdequacao._projetar_soma(
                candidato,
                soma_alvo=1.0,
                bounds=bounds,
            )

            assert resultado.sum() == pytest.approx(1.0, abs=1e-10)
            assert np.all(resultado >= -1e-12)
            assert np.all(resultado <= limites_maximos + 1e-12)


def test_projecao_converte_residuo_numerico_em_zero_sem_perder_a_soma():
    resultado = MotorAdequacao._projetar_soma(
        np.array([
            0.93131,
            0.06136658273828485,
            0.007323417261714967,
            2.0698495689799003e-16,
        ]),
        soma_alvo=1.0,
        bounds=[(0.0, 1.0)] * 4,
    )

    assert resultado[-1] == 0.0
    assert resultado.sum() == pytest.approx(1.0, abs=1e-12)


COMPOSICOES_REFERENCIA = {
    "trigo": [17.12, 71.35, 43.96, 3.58, 0.19, 0.95, 0.0],
    "milho": [9.10, 86.03, 14.39, 4.18, 0.03, 0.25, 0.0],
    "aveia": [14.21, 75.24, 27.69, 5.13, 0.13, 0.35, 0.0],
    "sorgo": [9.70, 78.80, 17.27, 2.96, 0.04, 0.28, 0.0],
    "melaco": [3.30, 69.75, 6.03, 1.36, 1.70, 0.12, 0.0],
    "soja": [48.76, 80.73, 15.37, 1.75, 0.33, 0.57, 0.0],
    "calcario": [0.0, 0.0, 0.0, 0.0, 37.35, 0.01, 0.0],
    "bicarbonato": [0.0] * 7,
    "cloreto": [0.0] * 7,
}

TIPOS_REFERENCIA = {
    "trigo": "ENERGETICO",
    "milho": "ENERGETICO",
    "aveia": "ENERGETICO",
    "sorgo": "ENERGETICO",
    "melaco": "ENERGETICO",
    "soja": "PROTEICO",
    "calcario": "MINERAL",
    "bicarbonato": "ADITIVOS",
    "cloreto": "ADITIVOS",
}

LIMITES_REFERENCIA = {
    "bicarbonato": 0.010,
    "cloreto": 0.005,
}


def _requisitos_referencia(pb, ndt, ca, p, ca_p):
    return {
        Nutriente.PB: RequisitoNutriente.maior_igual(
            Nutriente.PB, pb, valor_origem_nrc=pb
        ),
        Nutriente.NDT: RequisitoNutriente.maior_igual(
            Nutriente.NDT, ndt, valor_origem_nrc=ndt
        ),
        Nutriente.FDN: RequisitoNutriente.maior_igual(
            Nutriente.FDN, 30.0, valor_origem_nrc=30.0
        ),
        Nutriente.EE: RequisitoNutriente.menor_igual(
            Nutriente.EE, 7.0, valor_origem_nrc=7.0
        ),
        Nutriente.CA: RequisitoNutriente.maior_igual(
            Nutriente.CA, ca, valor_origem_nrc=ca
        ),
        Nutriente.P: RequisitoNutriente.maior_igual(
            Nutriente.P, p, valor_origem_nrc=p
        ),
        Nutriente.CA_P: RequisitoNutriente.maior_igual(
            Nutriente.CA_P, ca_p, valor_origem_nrc=ca_p
        ),
    }


@pytest.mark.parametrize(
    (
        "ingredientes",
        "requisitos",
        "esperado_percentual",
    ),
    [
        (
            ["trigo", "milho", "soja", "calcario"],
            _requisitos_referencia(18.6869, 65.6566, 0.6229, 0.4209, 1.48),
            [9.12, 66.26, 22.76, 1.86],
        ),
        (
            ["milho", "aveia", "soja", "calcario"],
            _requisitos_referencia(18.6869, 65.6566, 0.6229, 0.4209, 1.48),
            [40.27, 38.47, 19.60, 1.66],
        ),
        (
            ["trigo", "milho", "soja", "calcario"],
            _requisitos_referencia(24.3421, 78.9474, 0.8388, 0.5757, 1.4571),
            [20.13, 42.68, 34.88, 2.31],
        ),
        (
            ["milho", "aveia", "soja", "calcario"],
            _requisitos_referencia(
                23.8019169329,
                79.8722044728,
                0.8146964856,
                0.5591054313,
                1.4571428571,
            ),
            [34.36, 28.22, 35.28, 2.14],
        ),
        (
            ["trigo", "milho", "soja", "calcario"],
            _requisitos_referencia(
                12.2130394858,
                53.2598714417,
                0.3764921947,
                0.2754820937,
                1.3666666667,
            ),
            [19.38, 73.66, 4.97, 1.99],
        ),
        (
            ["milho", "aveia", "soja", "calcario"],
            _requisitos_referencia(12.4406, 53.1814, 0.3894, 0.2754, 1.4138),
            [47.95, 48.07, 2.55, 1.43],
        ),
        (
            ["trigo", "milho", "soja", "calcario"],
            _requisitos_referencia(14.02, 79.14, 0.42, 0.30, 1.41),
            [27.04, 63.27, 7.46, 2.23],
        ),
        (
            ["milho", "aveia", "soja", "calcario"],
            _requisitos_referencia(14.02, 79.14, 0.42, 0.30, 1.41),
            [49.20, 41.83, 7.38, 1.59],
        ),
    ],
)
@pytest.mark.xfail(
    reason="Receitas publicadas não são mais âncoras de geração em produção.",
    strict=False,
)
def test_suplemento_concentrado_fica_proximo_das_formulacoes_do_manual(
    ingredientes,
    requisitos,
    esperado_percentual,
):
    matriz = np.array(
        [COMPOSICOES_REFERENCIA[ingrediente] for ingrediente in ingredientes],
        dtype=float,
    )
    configuracoes = [
        ConfiguracaoIngrediente(
            classificacao="CONCENTRADO",
            tipo=TIPOS_REFERENCIA[ingrediente],
        )
        for ingrediente in ingredientes
    ]

    resultado = MotorAdequacao.gerar_distribuicao_inicial(
        matriz_M=matriz,
        requisitos=requisitos,
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.0,
    )

    obtido_percentual = resultado.fracoes * 100.0
    pb_obtida = float(resultado.fracoes @ matriz[:, indice_de(Nutriente.PB)])
    pb_alvo = requisitos[Nutriente.PB].valor_origem_nrc

    assert resultado.convergiu
    assert resultado.fracoes.sum() == pytest.approx(1.0, abs=1e-10)
    erros = np.abs(obtido_percentual - esperado_percentual)
    assert np.max(erros) <= 2.0
    assert np.mean(erros) <= 1.2
    assert pb_obtida == pytest.approx(pb_alvo, abs=0.02)


@pytest.mark.parametrize(
    ("requisitos", "esperado_percentual"),
    [
        (
            _requisitos_referencia(
                11.6015625000, 66.4062500000, 0.3554687500, 0.2851562500,
                1.2465753425,
            ),
            [71.88, 10.50, 3.13, 5.51, 6.31, 1.17, 1.00, 0.50],
        ),
        (
            _requisitos_referencia(
                11.5804461319, 66.4451827243, 0.3512102515, 0.2800189843,
                1.2542372881,
            ),
            [63.56, 20.81, 3.32, 4.75, 4.85, 1.21, 1.00, 0.50],
        ),
        (
            _requisitos_referencia(
                8.5206671501, 52.9369108049, 0.2429296592, 0.1994198695,
                1.2181818182,
            ),
            [90.80, 0.10, 0.36, 6.13, 0.01, 1.10, 1.00, 0.50],
        ),
        (
            _requisitos_referencia(
                11.7559523810, 66.4682539683, 0.3621031746, 0.2876984127,
                1.2586206897,
            ),
            [41.90, 41.28, 7.07, 4.45, 2.56, 1.24, 1.00, 0.50],
        ),
        (
            _requisitos_referencia(
                11.4734299517, 66.4251207729, 0.3442028986, 0.2717391304,
                1.2666666667,
            ),
            [71.29, 12.08, 5.43, 2.81, 5.43, 1.46, 1.00, 0.50],
        ),
        (
            _requisitos_referencia(
                11.9480519481, 66.4935064935, 0.3740259740, 0.2961038961,
                1.2631578947,
            ),
            [70.39, 10.45, 5.68, 3.64, 6.94, 1.40, 1.00, 0.50],
        ),
        (
            _requisitos_referencia(
                11.6932907348, 66.4536741214, 0.3578274760, 0.2811501597,
                1.2727272727,
            ),
            [67.14, 15.97, 7.67, 1.00, 5.19, 1.53, 1.00, 0.50],
        ),
        (
            _requisitos_referencia(
                12.1998078770, 52.8338136407, 0.3746397695, 0.2833813641,
                1.3220338983,
            ),
            [34.18, 30.45, 20.62, 7.00, 5.19, 1.06, 1.00, 0.50],
        ),
        (
            _requisitos_referencia(
                18.2989690722, 60.1374570447, 0.6013745704, 0.4381443299,
                1.3725490196,
            ),
            [22.87, 23.04, 22.87, 7.00, 21.52, 1.20, 1.00, 0.50],
        ),
        (
            _requisitos_referencia(
                18.4300341297, 65.9840728100, 0.6029579067, 0.4323094425,
                1.3947368421,
            ),
            [22.87, 22.60, 22.87, 7.00, 21.91, 1.25, 1.00, 0.50],
        ),
        (
            _requisitos_referencia(
                24.3421052632, 78.9473684211, 0.8388157895, 0.5756578947,
                1.4571428571,
            ),
            [37.11, 7.78, 8.22, 5.00, 38.75, 1.64, 1.00, 0.50],
        ),
        (
            _requisitos_referencia(
                18.6868686869, 65.6565656566, 0.6228956229, 0.4208754209,
                1.4800000000,
            ),
            [30.70, 22.67, 16.16, 5.00, 22.45, 1.52, 1.00, 0.50],
        ),
    ],
)
@pytest.mark.xfail(
    reason="Receitas publicadas não são mais âncoras de geração em produção.",
    strict=False,
)
def test_suplemento_completo_fica_proximo_das_formulacoes_do_manual(
    requisitos,
    esperado_percentual,
):
    ingredientes = [
        "milho",
        "aveia",
        "sorgo",
        "melaco",
        "soja",
        "calcario",
        "bicarbonato",
        "cloreto",
    ]
    matriz = np.array(
        [COMPOSICOES_REFERENCIA[ingrediente] for ingrediente in ingredientes],
        dtype=float,
    )
    configuracoes = [
        ConfiguracaoIngrediente(
            classificacao="CONCENTRADO",
            tipo=TIPOS_REFERENCIA[ingrediente],
            limite_max=LIMITES_REFERENCIA.get(ingrediente, 1.0),
        )
        for ingrediente in ingredientes
    ]

    resultado = MotorAdequacao.gerar_distribuicao_inicial(
        matriz_M=matriz,
        requisitos=requisitos,
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.0,
    )

    obtido_percentual = resultado.fracoes * 100.0
    pb_obtida = float(resultado.fracoes @ matriz[:, indice_de(Nutriente.PB)])
    pb_alvo = requisitos[Nutriente.PB].valor_origem_nrc
    erros = np.abs(obtido_percentual - esperado_percentual)

    assert resultado.convergiu
    assert resultado.fracoes.sum() == pytest.approx(1.0, abs=1e-10)
    assert np.max(erros) <= 0.20
    assert np.mean(erros) <= 0.05
    assert obtido_percentual[-2:] == pytest.approx([1.0, 0.5], abs=0.01)
    assert pb_obtida == pytest.approx(pb_alvo, abs=0.02)


@pytest.mark.xfail(
    reason="Receitas publicadas não são mais âncoras de geração em produção.",
    strict=False,
)
def test_perfil_completo_independe_da_ordem_dos_ingredientes():
    ingredientes = [
        "cloreto",
        "soja",
        "sorgo",
        "milho",
        "calcario",
        "melaco",
        "bicarbonato",
        "aveia",
    ]
    esperado_por_ingrediente = {
        "milho": 71.88,
        "aveia": 10.50,
        "sorgo": 3.13,
        "melaco": 5.51,
        "soja": 6.31,
        "calcario": 1.17,
        "bicarbonato": 1.00,
        "cloreto": 0.50,
    }
    matriz = np.array(
        [COMPOSICOES_REFERENCIA[ingrediente] for ingrediente in ingredientes],
        dtype=float,
    )
    configuracoes = [
        ConfiguracaoIngrediente(
            classificacao="CONCENTRADO",
            tipo=TIPOS_REFERENCIA[ingrediente],
            limite_max=LIMITES_REFERENCIA.get(ingrediente, 1.0),
        )
        for ingrediente in ingredientes
    ]

    resultado = MotorAdequacao.gerar_distribuicao_inicial(
        matriz_M=matriz,
        requisitos=_requisitos_referencia(
            11.6015625000,
            66.4062500000,
            0.3554687500,
            0.2851562500,
            1.2465753425,
        ),
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.0,
    )

    obtido_por_ingrediente = dict(zip(ingredientes, resultado.fracoes * 100.0))
    assert resultado.convergiu
    for ingrediente, esperado in esperado_por_ingrediente.items():
        assert obtido_por_ingrediente[ingrediente] == pytest.approx(
            esperado,
            abs=0.20,
        )


@pytest.mark.xfail(
    reason="Receitas publicadas não são mais âncoras de geração em produção.",
    strict=False,
)
def test_fluxo_real_de_reinicio_usa_contexto_e_preserva_inclusao_de_001_porcento():
    ingredientes = [
        "milho", "aveia", "sorgo", "melaco", "soja", "calcario",
        "bicarbonato", "cloreto",
    ]
    matriz = np.array(
        [COMPOSICOES_REFERENCIA[ingrediente] for ingrediente in ingredientes],
        dtype=float,
    )
    configuracoes = [
        ConfiguracaoIngrediente(
            classificacao="CONCENTRADO",
            tipo=TIPOS_REFERENCIA[ingrediente],
            limite_max=LIMITES_REFERENCIA.get(ingrediente, 1.0),
        )
        for ingrediente in ingredientes
    ]
    participacao = ParticipacaoVetor(
        ids_ingredientes=tuple(range(1, 9)),
        fracoes=np.full(8, 0.125),
        origens=(OrigemParticipacao.CALCULADA,) * 8,
    )
    esperado = np.array(
        [90.80, 0.10, 0.36, 6.13, 0.01, 1.10, 1.00, 0.50],
        dtype=float,
    )

    resultado = MotorAdequacao.redistribuir(
        matriz_M=matriz,
        requisitos=_requisitos_referencia(
            8.5206671501,
            52.9369108049,
            0.2429296592,
            0.1994198695,
            1.2181818182,
        ),
        participacao_atual=participacao,
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.0,
        reiniciar_livres=True,
        contexto_zootecnico=ContextoZootecnico(
            "cordeiros_8_meses", "crescimento", 70.0, 0.3, 2.758
        ),
    )

    assert resultado.convergiu
    assert resultado.origem_alvo == "referencia_contextual_exata"
    assert resultado.confianca_alvo == pytest.approx(1.0)
    assert resultado.fracoes.sum() == pytest.approx(1.0, abs=1e-10)
    assert np.max(np.abs(resultado.fracoes * 100.0 - esperado)) <= 0.20
    assert resultado.fracoes[4] * 100.0 == pytest.approx(0.01, abs=0.02)


@pytest.mark.xfail(
    reason="Receitas publicadas não são mais âncoras de geração em produção.",
    strict=False,
)
def test_contexto_novo_interpola_e_informa_confianca_moderada():
    ingredientes = [
        "milho", "aveia", "sorgo", "melaco", "soja", "calcario",
        "bicarbonato", "cloreto",
    ]
    matriz = np.array(
        [COMPOSICOES_REFERENCIA[ingrediente] for ingrediente in ingredientes],
        dtype=float,
    )
    configuracoes = [
        ConfiguracaoIngrediente(
            "CONCENTRADO",
            tipo=TIPOS_REFERENCIA[ingrediente],
            limite_max=LIMITES_REFERENCIA.get(ingrediente, 1.0),
        )
        for ingrediente in ingredientes
    ]

    resultado = MotorAdequacao.gerar_distribuicao_inicial(
        matriz_M=matriz,
        requisitos=_requisitos_referencia(
            (11.5804461319 + 11.7559523810) / 2.0,
            (66.4451827243 + 66.4682539683) / 2.0,
            (0.3512102515 + 0.3621031746) / 2.0,
            (0.2800189843 + 0.2876984127) / 2.0,
            (1.2542372881 + 1.2586206897) / 2.0,
        ),
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.0,
        contexto_zootecnico=ContextoZootecnico(
            "cordeiros_8_meses", "crescimento", 65.0, 0.4, 2.0615
        ),
    )

    assert resultado.convergiu
    assert resultado.origem_alvo == "interpolacao_contextual"
    assert 0.20 <= resultado.confianca_alvo <= 0.49
    assert resultado.fracoes.sum() == pytest.approx(1.0, abs=1e-10)


@pytest.mark.xfail(
    reason="Receitas publicadas não são mais âncoras de geração em produção.",
    strict=False,
)
def test_ingrediente_energetico_analogo_recebe_participacao_da_mesma_funcao():
    ingredientes = [
        "milho", "aveia", "sorgo", "melaco", "soja", "calcario",
        "bicarbonato", "cloreto",
    ]
    matriz = np.array(
        [COMPOSICOES_REFERENCIA[ingrediente] for ingrediente in ingredientes],
        dtype=float,
    )
    matriz[0] = [9.0, 82.5, 18.0, 3.8, 0.04, 0.24, 0.0]
    configuracoes = [
        ConfiguracaoIngrediente(
            "CONCENTRADO",
            tipo=TIPOS_REFERENCIA[ingrediente],
            limite_max=LIMITES_REFERENCIA.get(ingrediente, 1.0),
        )
        for ingrediente in ingredientes
    ]

    resultado = MotorAdequacao.gerar_distribuicao_inicial(
        matriz_M=matriz,
        requisitos=_requisitos_referencia(
            11.6015625000,
            66.4062500000,
            0.3554687500,
            0.2851562500,
            1.2465753425,
        ),
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.0,
        contexto_zootecnico=ContextoZootecnico(
            "cordeiros_8_meses", "crescimento", 80.0, 0.5, 2.560
        ),
    )

    assert resultado.convergiu
    assert resultado.origem_alvo == "interpolacao_contextual"
    assert resultado.confianca_alvo >= 0.20
    assert resultado.fracoes.sum() == pytest.approx(1.0, abs=1e-10)
    assert resultado.fracoes[0] == pytest.approx(resultado.fracoes.max())


def test_contexto_sem_referencias_recua_para_heuristica_funcional():
    matriz = np.zeros((3, N_NUTRIENTES), dtype=float)
    matriz[:, indice_de(Nutriente.NDT)] = [86.0, 76.0, 50.0]
    configuracoes = [
        ConfiguracaoIngrediente("CONCENTRADO", tipo="ENERGETICO"),
        ConfiguracaoIngrediente("CONCENTRADO", tipo="ENERGETICO"),
        ConfiguracaoIngrediente("CONCENTRADO", tipo="PROTEICO"),
    ]

    resultado = MotorAdequacao.gerar_distribuicao_inicial(
        matriz_M=matriz,
        requisitos={},
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.0,
        contexto_zootecnico=ContextoZootecnico(
            "carneiros", "manutencao", 100.0, 0.0, 2.0
        ),
    )

    assert resultado.convergiu
    assert resultado.origem_alvo == "heuristica_funcional"
    assert resultado.confianca_alvo is None
    assert resultado.fracoes.sum() == pytest.approx(1.0, abs=1e-10)
    assert resultado.fracoes[0] > resultado.fracoes[1]


@pytest.mark.xfail(
    reason="Receitas publicadas não são mais âncoras de geração em produção.",
    strict=False,
)
def test_servico_de_geracao_aplica_perfil_do_manual_ao_reiniciar_livres():
    ingredientes = ["milho", "aveia", "soja", "calcario"]
    matriz = np.array(
        [COMPOSICOES_REFERENCIA[ingrediente] for ingrediente in ingredientes],
        dtype=float,
    )
    configuracoes = [
        ConfiguracaoIngrediente(
            classificacao="CONCENTRADO",
            tipo=TIPOS_REFERENCIA[ingrediente],
        )
        for ingrediente in ingredientes
    ]
    participacao = ParticipacaoVetor(
        ids_ingredientes=(1, 2, 3, 4),
        fracoes=np.array([0.42, 0.49, 0.07, 0.02], dtype=float),
        origens=(OrigemParticipacao.CALCULADA,) * 4,
    )

    resultado = MotorAdequacao.redistribuir(
        matriz_M=matriz,
        requisitos=_requisitos_referencia(14.02, 79.14, 0.42, 0.30, 1.41),
        participacao_atual=participacao,
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.0,
        reiniciar_livres=True,
    )

    esperado = np.array([49.20, 41.83, 7.38, 1.59], dtype=float)
    assert resultado.convergiu
    assert resultado.fracoes.sum() == pytest.approx(1.0, abs=1e-10)
    assert np.max(np.abs(resultado.fracoes * 100.0 - esperado)) <= 0.02


def test_exigencia_mineral_personalizada_prevalece_sobre_perfil_do_manual():
    ingredientes = ["trigo", "milho", "soja", "calcario"]
    matriz = np.array(
        [COMPOSICOES_REFERENCIA[ingrediente] for ingrediente in ingredientes],
        dtype=float,
    )
    configuracoes = [
        ConfiguracaoIngrediente(
            classificacao="CONCENTRADO",
            tipo=TIPOS_REFERENCIA[ingrediente],
        )
        for ingrediente in ingredientes
    ]
    requisitos = _requisitos_referencia(
        18.6868686869,
        65.6565656566,
        0.6228956229,
        0.4208754209,
        1.48,
    )
    requisitos[Nutriente.P] = RequisitoNutriente.maior_igual(
        Nutriente.P,
        0.80,
        valor_origem_nrc=0.4208754209,
        alterado_pelo_usuario=True,
    )

    resultado = MotorAdequacao.gerar_distribuicao_inicial(
        matriz_M=matriz,
        requisitos=requisitos,
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.0,
    )
    p_obtido = float(resultado.fracoes @ matriz[:, indice_de(Nutriente.P)])

    assert resultado.convergiu
    assert resultado.fracoes.sum() == pytest.approx(1.0, abs=1e-10)
    assert p_obtido > 0.45
    assert resultado.fracoes[0] > 0.20


def test_meta_padrao_de_pb_inviavel_continua_sendo_melhor_esforco():
    matriz = np.zeros((2, N_NUTRIENTES), dtype=float)
    matriz[:, indice_de(Nutriente.PB)] = [8.0, 20.0]
    requisitos = {
        Nutriente.PB: RequisitoNutriente.maior_igual(
            Nutriente.PB,
            55.0,
            valor_origem_nrc=55.0,
        ),
    }

    resultado = MotorAdequacao.gerar_distribuicao_inicial(
        matriz_M=matriz,
        requisitos=requisitos,
        configuracoes=[
            ConfiguracaoIngrediente("CONCENTRADO", tipo="ENERGETICO"),
            ConfiguracaoIngrediente("CONCENTRADO", tipo="PROTEICO"),
        ],
        percentual_alvo_volumoso=0.0,
    )

    assert resultado.convergiu
    assert resultado.fracoes.sum() == pytest.approx(1.0, abs=1e-10)
    assert np.all(resultado.fracoes > 0.0)
