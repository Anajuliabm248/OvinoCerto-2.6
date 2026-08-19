import numpy as np
import pytest

from formulacao.domain.nutrientes import Nutriente
from formulacao.domain.requisito import RequisitoNutriente
from formulacao.engines.estimador_referencia import (
    ContextoZootecnico,
    EstimadorPreferenciaAprendida,
    EstimadorReceitaReferencia,
    IngredienteReferencia,
    ReferenciaSuplemento,
    REFERENCIAS_SUPLEMENTO_COMPLETO,
)


def _requisitos(referencia):
    return {
        Nutriente.PB: RequisitoNutriente.maior_igual(
            Nutriente.PB, referencia.pb, valor_origem_nrc=referencia.pb
        ),
        Nutriente.NDT: RequisitoNutriente.maior_igual(
            Nutriente.NDT, referencia.ndt, valor_origem_nrc=referencia.ndt
        ),
        Nutriente.CA: RequisitoNutriente.maior_igual(
            Nutriente.CA, referencia.ca, valor_origem_nrc=referencia.ca
        ),
        Nutriente.P: RequisitoNutriente.maior_igual(
            Nutriente.P, referencia.p, valor_origem_nrc=referencia.p
        ),
        Nutriente.CA_P: RequisitoNutriente.maior_igual(
            Nutriente.CA_P, referencia.ca_p, valor_origem_nrc=referencia.ca_p
        ),
    }


def _requisitos_interpolados(a, b):
    valores = {
        Nutriente.PB: (a.pb + b.pb) / 2.0,
        Nutriente.NDT: (a.ndt + b.ndt) / 2.0,
        Nutriente.CA: (a.ca + b.ca) / 2.0,
        Nutriente.P: (a.p + b.p) / 2.0,
        Nutriente.CA_P: (a.ca_p + b.ca_p) / 2.0,
    }
    return {
        nutriente: RequisitoNutriente.maior_igual(
            nutriente, valor, valor_origem_nrc=valor
        )
        for nutriente, valor in valores.items()
    }


@pytest.mark.parametrize("referencia", REFERENCIAS_SUPLEMENTO_COMPLETO)
def test_contexto_exato_reproduz_referencia_sem_interpolar(referencia):
    estimativa = EstimadorReceitaReferencia.estimar(
        contexto=referencia.contexto,
        requisitos=_requisitos(referencia),
    )

    assert estimativa is not None
    assert estimativa.exata
    assert estimativa.confianca == pytest.approx(1.0)
    assert estimativa.receita == pytest.approx(referencia.receita, abs=1e-12)
    assert estimativa.receita.sum() == pytest.approx(1.0, abs=1e-12)


def test_contexto_intermediario_interpola_sem_escolher_receita_fechada():
    referencia_a = REFERENCIAS_SUPLEMENTO_COMPLETO[1]
    referencia_b = REFERENCIAS_SUPLEMENTO_COMPLETO[3]
    contexto = ContextoZootecnico(
        categoria="cordeiros_8_meses",
        fase="crescimento",
        peso_vivo_kg=65.0,
        gmd_kg=0.4,
        cms_kg=(referencia_a.contexto.cms_kg + referencia_b.contexto.cms_kg) / 2.0,
    )

    estimativa = EstimadorReceitaReferencia.estimar(
        contexto=contexto,
        requisitos=_requisitos_interpolados(referencia_a, referencia_b),
    )

    assert estimativa is not None
    assert not estimativa.exata
    assert 0.0 < estimativa.confianca < 1.0
    assert estimativa.receita.sum() == pytest.approx(1.0, abs=1e-12)
    assert not np.allclose(estimativa.receita, referencia_a.receita)
    assert not np.allclose(estimativa.receita, referencia_b.receita)


def test_extrapolacao_reduz_confianca_em_relacao_ao_contexto_intermediario():
    referencia_a = REFERENCIAS_SUPLEMENTO_COMPLETO[1]
    referencia_b = REFERENCIAS_SUPLEMENTO_COMPLETO[3]
    requisitos = _requisitos_interpolados(referencia_a, referencia_b)
    contexto_intermediario = ContextoZootecnico(
        "cordeiros_8_meses", "crescimento", 65.0, 0.4, 2.0615
    )
    contexto_extrapolado = ContextoZootecnico(
        "cordeiros_8_meses", "crescimento", 110.0, 0.7, 4.0
    )

    intermediaria = EstimadorReceitaReferencia.estimar(
        contexto_intermediario, requisitos
    )
    extrapolada = EstimadorReceitaReferencia.estimar(
        contexto_extrapolado, requisitos
    )

    assert intermediaria is not None
    assert extrapolada is not None
    assert extrapolada.confianca < intermediaria.confianca
    assert extrapolada.confianca < 0.10


def test_arredondamento_editorial_do_nrc_ainda_reconhece_cenario_exato():
    referencia = REFERENCIAS_SUPLEMENTO_COMPLETO[-1]
    requisitos = {
        Nutriente.PB: RequisitoNutriente.maior_igual(
            Nutriente.PB, referencia.pb + 0.0021,
            valor_origem_nrc=referencia.pb + 0.0021,
        ),
        Nutriente.NDT: RequisitoNutriente.maior_igual(
            Nutriente.NDT, referencia.ndt + 0.0014,
            valor_origem_nrc=referencia.ndt + 0.0014,
        ),
        Nutriente.CA: RequisitoNutriente.maior_igual(
            Nutriente.CA, referencia.ca - 0.0012,
            valor_origem_nrc=referencia.ca - 0.0012,
        ),
        Nutriente.P: RequisitoNutriente.maior_igual(
            Nutriente.P, referencia.p + 0.0043,
            valor_origem_nrc=referencia.p + 0.0043,
        ),
        Nutriente.CA_P: RequisitoNutriente.maior_igual(
            Nutriente.CA_P, referencia.ca_p - 0.0172,
            valor_origem_nrc=referencia.ca_p - 0.0172,
        ),
    }

    estimativa = EstimadorReceitaReferencia.estimar(
        referencia.contexto,
        requisitos,
        referencias=(referencia,),
    )

    assert estimativa is not None
    assert estimativa.exata
    assert estimativa.confianca == pytest.approx(1.0)


def test_preferencia_aprendida_preve_proteico_em_cenario_cego():
    """A previsão usa composição e exigência, não posição ou código da receita."""
    energia = (9.0, 84.0, 14.0, 4.0, 0.03, 0.25)
    proteico = (48.0, 80.0, 15.0, 2.0, 0.33, 0.57)
    referencias = []
    for indice, pb in enumerate(range(10, 28, 2)):
        participacao_proteico = 0.10 + 0.02 * (pb - 10)
        contexto = ContextoZootecnico(
            "cordeiros_4_meses", "crescimento", 20.0 + indice * 5.0,
            0.2 + indice * 0.01, 0.60 + indice * 0.05,
        )
        referencias.append(ReferenciaSuplemento(
            contexto=contexto, pb=float(pb), ndt=70.0, ca=0.4, p=0.3, ca_p=1.3,
            receita=(1.0 - participacao_proteico, participacao_proteico),
            codigo=f"APRENDIZADO-{indice}",
            ingredientes=(
                IngredienteReferencia("CONCENTRADO", "ENERGETICO", 1.0 - participacao_proteico, energia),
                IngredienteReferencia("CONCENTRADO", "PROTEICO", participacao_proteico, proteico),
            ),
        ))

    referencia_oculta = referencias[4]
    treino = tuple(item for item in referencias if item != referencia_oculta)
    estimativa = EstimadorPreferenciaAprendida.estimar(
        contexto=referencia_oculta.contexto,
        requisitos=_requisitos(referencia_oculta),
        matriz_M=np.array([[*proteico, 0.0], [*energia, 0.0]]),
        classificacoes=("CONCENTRADO", "CONCENTRADO"),
        tipos=("PROTEICO", "ENERGETICO"),
        limites_max=(1.0, 1.0),
        referencias=treino,
        confianca_contextual=0.40,
    )

    assert estimativa is not None
    assert estimativa.referencias_treinamento == len(treino)
    assert estimativa.fracoes.sum() == pytest.approx(1.0)
    assert estimativa.fracoes[0] == pytest.approx(0.26, abs=0.10)
    assert estimativa.confianca <= 0.49


@pytest.mark.parametrize("indice", range(len(REFERENCIAS_SUPLEMENTO_COMPLETO)))
def test_validacao_cega_nao_declara_alta_confianca_quando_vizinhos_divergem(indice):
    referencia = REFERENCIAS_SUPLEMENTO_COMPLETO[indice]
    referencias_treino = tuple(
        item
        for posicao, item in enumerate(REFERENCIAS_SUPLEMENTO_COMPLETO)
        if posicao != indice
    )
    estimativa = EstimadorReceitaReferencia.estimar(
        contexto=referencia.contexto,
        requisitos=_requisitos(referencia),
        referencias=referencias_treino,
    )

    assert estimativa is not None
    erro_maximo = float(np.max(
        np.abs(estimativa.receita - np.asarray(referencia.receita)) * 100.0
    ))
    if erro_maximo > 5.0:
        assert estimativa.confianca < 0.50
