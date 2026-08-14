"""Regressões do ranking funcional do MotorSugestao."""

import numpy as np
import pytest

from formulacao.domain.nutrientes import NUTRIENTES_ORDEM, Nutriente, indice_de
from formulacao.engines.motor_sugestao import CandidatoSugestao, MotorSugestao


def _vetor(*, pb=0.0, ndt=0.0, fdn=0.0, ee=0.0, ca=0.0, p=0.0):
    vetor = np.zeros(len(NUTRIENTES_ORDEM), dtype=float)
    valores = {
        Nutriente.PB: pb,
        Nutriente.NDT: ndt,
        Nutriente.FDN: fdn,
        Nutriente.EE: ee,
        Nutriente.CA: ca,
        Nutriente.P: p,
    }
    for nutriente, valor in valores.items():
        vetor[indice_de(nutriente)] = valor
    if p > 1e-9:
        vetor[indice_de(Nutriente.CA_P)] = ca / p
    return vetor


def _candidato(
    ingrediente_id,
    nome,
    tipo,
    *,
    classificacao="concentrado",
    custo=1.0,
    **nutrientes,
):
    return CandidatoSugestao(
        ingrediente_id=ingrediente_id,
        nome=nome,
        classificacao=classificacao,
        tipo=tipo,
        custo_kg=custo,
        ms_percentual=90.0,
        vetor=_vetor(**nutrientes),
    )


def _desvio(nutriente, magnitude=0.5, status="DEFICIT"):
    return {
        "nutriente": nutriente.value,
        "status": status,
        "magnitude_relativa": magnitude,
    }


def _sugerir_substitutos(original, candidatos, desvios):
    return MotorSugestao.sugerir(
        desvios_payload=desvios,
        candidatos=candidatos,
        vetor_total_atual=_vetor(pb=12, ndt=65, fdn=35, ee=3, ca=0.5, p=0.3),
        modo="substituir",
        vetor_substituido=original.vetor,
        fracao_substituido=0.10,
        candidato_substituido=original,
        max_resultados=20,
    )


def test_calcario_aceita_ostra_e_rejeita_milho():
    calcario = _candidato(1, "Calcário calcítico", "mineral", ca=37.35, p=0.01)
    ostra = _candidato(2, "Ostra Marinha", "mineral", ca=36.88, p=5.30)
    fosfato = _candidato(3, "Fosfato Bicálcico", "mineral", ca=24.16, p=18.50)
    milho = _candidato(4, "Milho Grão", "energetico", pb=9.1, ndt=86.0, fdn=14.4)

    resultado = _sugerir_substitutos(
        calcario,
        [milho, fosfato, ostra],
        [_desvio(Nutriente.CA)],
    )

    assert [item.nome for item in resultado][0] == "Ostra Marinha"
    assert "Milho Grão" not in [item.nome for item in resultado]
    assert resultado[0].delta_ca == pytest.approx(0.10 * (36.88 - 37.35))


def test_bicarbonato_rejeita_milho_antes_da_distancia():
    bicarbonato = _candidato(1, "Bicarbonato de Sódio", "aditivos")
    outro_tampao = _candidato(2, "Bicarbonato de Potássio", "aditivos")
    milho = _candidato(3, "Milho Grão", "energetico", pb=9.1, ndt=86.0, fdn=14.4)

    resultado = _sugerir_substitutos(
        bicarbonato,
        [milho, outro_tampao],
        [_desvio(Nutriente.NDT)],
    )

    assert [item.nome for item in resultado] == ["Bicarbonato de Potássio"]


def test_fosfato_bicalcico_prioriza_outra_fonte_de_ca_p():
    bicalcico = _candidato(1, "Fosfato Bicálcico", "mineral", ca=24.16, p=18.50)
    monocacico = _candidato(2, "Fosfato Monocálcico", "mineral", ca=19.97, p=21.97)
    calcario = _candidato(3, "Calcário", "mineral", ca=37.02, p=0.03)
    milho = _candidato(4, "Milho Grão", "energetico", pb=9.1, ndt=86.0, fdn=14.4)

    resultado = _sugerir_substitutos(
        bicalcico,
        [calcario, milho, monocacico],
        [_desvio(Nutriente.CA_P)],
    )

    assert resultado[0].nome == "Fosfato Monocálcico"
    assert "Milho Grão" not in [item.nome for item in resultado]


def test_necessidade_de_pb_prioriza_fonte_proteica_que_melhora_a_troca():
    soja = _candidato(1, "Farelo de Soja", "proteico", pb=48, ndt=80, fdn=15)
    gluten = _candidato(2, "Milho Glúten", "proteico", pb=63, ndt=90, fdn=6)
    algodao = _candidato(3, "Farelo de Algodão", "proteico", pb=41, ndt=70, fdn=24)
    milho = _candidato(4, "Milho Grão", "energetico", pb=9, ndt=86, fdn=14)

    resultado = _sugerir_substitutos(
        soja,
        [algodao, milho, gluten],
        [_desvio(Nutriente.PB, magnitude=0.8)],
    )

    assert resultado[0].nome == "Milho Glúten"
    assert "Milho Grão" not in [item.nome for item in resultado]


def test_custo_beneficio_usa_score_composto_sem_mudar_dto():
    milho = _candidato(1, "Milho Grão", "energetico", pb=9, ndt=86, fdn=14)
    caro = _candidato(2, "Sorgo caro", "energetico", custo=2.0, pb=10, ndt=90, fdn=16)
    barato = _candidato(3, "Sorgo barato", "energetico", custo=1.0, pb=10, ndt=90, fdn=16)
    prejudicial = _candidato(
        4, "Resíduo muito barato", "energetico", custo=0.01, pb=8, ndt=45, fdn=20,
    )

    resultado = MotorSugestao.sugerir(
        desvios_payload=[_desvio(Nutriente.NDT)],
        candidatos=[caro, prejudicial, barato],
        vetor_total_atual=_vetor(pb=12, ndt=65, fdn=35, ee=3, ca=0.5, p=0.3),
        modo="substituir",
        criterio="custo_beneficio",
        vetor_substituido=milho.vetor,
        fracao_substituido=0.20,
        candidato_substituido=milho,
    )

    assert resultado[0].nome == "Sorgo barato"
    assert resultado[0].indice_custo_beneficio is not None
    assert resultado[-1].nome == "Resíduo muito barato"
    assert resultado[-1].indice_custo_beneficio is None
    assert set(vars(resultado[0])) == {
        "ingrediente_id", "nome", "classificacao", "tipo", "custo_kg",
        "pb", "ndt", "fdn", "ee", "ca", "p", "score",
        "distancia_euclidiana", "custo_kg_ms", "indice_custo_beneficio",
        "delta_pb", "delta_ndt", "delta_fdn", "delta_ee", "delta_ca", "delta_p",
    }
