import numpy as np
import pytest

from formulacao.domain.participacao import OrigemParticipacao, ParticipacaoVetor
from formulacao.engines.motor_adequacao import ConfiguracaoIngrediente
from formulacao.services.ajustar_participacao_service import AjustarParticipacaoService


def _participacao() -> ParticipacaoVetor:
    return ParticipacaoVetor(
        ids_ingredientes=(1, 2, 3),
        fracoes=np.array([0.40, 0.30, 0.30], dtype=float),
        origens=(
            OrigemParticipacao.CALCULADA,
            OrigemParticipacao.CALCULADA,
            OrigemParticipacao.CALCULADA,
        ),
    )


def test_travamento_rejeita_valor_acima_do_limite_do_proprio_ingrediente():
    configuracoes = {
        1: ConfiguracaoIngrediente("CONCENTRADO", limite_max=0.20),
        2: ConfiguracaoIngrediente("CONCENTRADO"),
        3: ConfiguracaoIngrediente("CONCENTRADO"),
    }

    with pytest.raises(ValueError, match="limite máximo cadastrado"):
        AjustarParticipacaoService._validar_travamento_possivel(
            participacao_atual=_participacao(),
            ing_form_id=1,
            nova_fracao=0.25,
            configuracoes_por_id=configuracoes,
        )


def test_travamento_rejeita_sobra_acima_da_capacidade_dos_livres():
    configuracoes = {
        1: ConfiguracaoIngrediente("CONCENTRADO"),
        2: ConfiguracaoIngrediente("CONCENTRADO", limite_max=0.10),
        3: ConfiguracaoIngrediente("CONCENTRADO", limite_max=0.05),
    }

    with pytest.raises(ValueError, match="limites cadastrados permitem"):
        AjustarParticipacaoService._validar_travamento_possivel(
            participacao_atual=_participacao(),
            ing_form_id=1,
            nova_fracao=0.80,
            configuracoes_por_id=configuracoes,
        )


def test_travamento_aceita_quando_capacidade_restante_fecha_cem():
    configuracoes = {
        1: ConfiguracaoIngrediente("CONCENTRADO"),
        2: ConfiguracaoIngrediente("CONCENTRADO", limite_max=0.10),
        3: ConfiguracaoIngrediente("CONCENTRADO", limite_max=0.05),
    }

    tem_livre = AjustarParticipacaoService._validar_travamento_possivel(
        participacao_atual=_participacao(),
        ing_form_id=1,
        nova_fracao=0.85,
        configuracoes_por_id=configuracoes,
    )

    assert tem_livre is True
