import numpy as np
import pytest

from formulacao.domain.nutrientes import N_NUTRIENTES, Nutriente, indice_de
from formulacao.domain.participacao import OrigemParticipacao, ParticipacaoVetor
from formulacao.domain.requisito import RequisitoNutriente
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
    "soja": [48.76, 80.73, 15.37, 1.75, 0.33, 0.57, 0.0],
    "calcario": [0.0, 0.0, 0.0, 0.0, 37.35, 0.01, 0.0],
}

TIPOS_REFERENCIA = {
    "trigo": "ENERGETICO",
    "milho": "ENERGETICO",
    "aveia": "ENERGETICO",
    "soja": "PROTEICO",
    "calcario": "MINERAL",
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
