import numpy as np
import pytest

from formulacao.domain.participacao import OrigemParticipacao, ParticipacaoVetor
from formulacao.engines.motor_adequacao import ConfiguracaoIngrediente, MotorAdequacao


def test_redistribuir_reiniciando_livres_respeita_travados_e_alvo_volumoso():
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
        matriz_M=np.zeros((3, 6), dtype=float),
        requisitos={},
        participacao_atual=participacao,
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.75,
        reiniciar_livres=True,
    )

    assert resultado.convergiu
    assert resultado.fracoes[0] == pytest.approx(0.20)
    assert resultado.fracoes[1] == pytest.approx(0.60)
    assert resultado.fracoes[2] == pytest.approx(0.20)
    assert resultado.fracoes.sum() == pytest.approx(1.0)
