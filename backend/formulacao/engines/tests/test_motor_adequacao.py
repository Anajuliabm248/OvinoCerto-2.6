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
