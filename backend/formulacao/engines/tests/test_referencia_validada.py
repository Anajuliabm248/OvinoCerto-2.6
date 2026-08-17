"""Protege o uso das referências como guia técnico, não como tabela de IDs."""

import numpy as np
import pytest

from formulacao.domain.nutrientes import Nutriente
from formulacao.domain.requisito import RequisitoNutriente
from formulacao.engines.estimador_referencia import (
    ContextoZootecnico,
    IngredienteReferencia,
    ReferenciaSuplemento,
)
from formulacao.engines.motor_adequacao import ConfiguracaoIngrediente, MotorAdequacao


def _requisitos():
    return {
        Nutriente.PB: RequisitoNutriente.maior_igual(Nutriente.PB, 16.0, valor_origem_nrc=16.0),
        Nutriente.NDT: RequisitoNutriente.maior_igual(Nutriente.NDT, 70.0, valor_origem_nrc=70.0),
        Nutriente.CA: RequisitoNutriente.maior_igual(Nutriente.CA, 0.4, valor_origem_nrc=0.4),
        Nutriente.P: RequisitoNutriente.maior_igual(Nutriente.P, 0.3, valor_origem_nrc=0.3),
        Nutriente.CA_P: RequisitoNutriente.maior_igual(Nutriente.CA_P, 1.3, valor_origem_nrc=1.3),
    }


def test_referencia_exata_mapeia_por_assinatura_e_nao_por_ordem_ou_id():
    energia = (9.0, 82.0, 15.0, 4.0, 0.03, 0.25)
    proteico = (49.0, 81.0, 15.0, 2.0, 0.33, 0.57)
    referencia = ReferenciaSuplemento(
        contexto=ContextoZootecnico("cordeiros_4_meses", "crescimento", 30.0, 0.3, 1.0),
        pb=16.0, ndt=70.0, ca=0.4, p=0.3, ca_p=1.3,
        receita=(0.70, 0.30),
        codigo="TESTE-ASSINATURA",
        ingredientes=(
            IngredienteReferencia("CONCENTRADO", "ENERGETICO", 0.70, energia),
            IngredienteReferencia("CONCENTRADO", "PROTEICO", 0.30, proteico),
        ),
    )
    # A ordem recebida é propositalmente a inversa da referência.
    matriz = np.array([
        [*proteico, 0.0],
        [*energia, 0.0],
    ])
    configuracoes = [
        ConfiguracaoIngrediente("CONCENTRADO", tipo="PROTEICO"),
        ConfiguracaoIngrediente("CONCENTRADO", tipo="ENERGETICO"),
    ]

    destino, usa_referencia, origem, confianca = MotorAdequacao._preparar_x_alvo(
        configuracoes=configuracoes,
        percentual_volumoso=0.0,
        matriz_M=matriz,
        requisitos=_requisitos(),
        contexto_zootecnico=referencia.contexto,
        referencias_suplemento=(referencia,),
    )

    assert destino == pytest.approx([0.30, 0.70])
    assert usa_referencia
    assert origem == "referencia_validada_exata:TESTE-ASSINATURA"
    assert confianca == pytest.approx(1.0)


def test_referencia_distante_nao_vira_uma_regra_de_alta_confianca():
    contexto = ContextoZootecnico("cordeiros_4_meses", "crescimento", 30.0, 0.3, 1.0)
    referencia = ReferenciaSuplemento(
        contexto=contexto, pb=16.0, ndt=70.0, ca=0.4, p=0.3, ca_p=1.3,
        receita=(1.0,), codigo="TESTE-GUIA",
        ingredientes=(IngredienteReferencia(
            "CONCENTRADO", "ENERGETICO", 1.0, (9.0, 82.0, 15.0, 4.0, 0.03, 0.25)
        ),),
    )
    matriz = np.array([[9.0, 82.0, 15.0, 4.0, 0.03, 0.25, 0.0]])
    configuracoes = [ConfiguracaoIngrediente("CONCENTRADO", tipo="ENERGETICO")]
    contexto_distante = ContextoZootecnico("cordeiros_4_meses", "crescimento", 90.0, 0.7, 3.0)

    _, usa_referencia, _, confianca = MotorAdequacao._preparar_x_alvo(
        configuracoes=configuracoes,
        percentual_volumoso=0.0,
        matriz_M=matriz,
        requisitos=_requisitos(),
        contexto_zootecnico=contexto_distante,
        referencias_suplemento=(referencia,),
    )

    assert not usa_referencia
    assert confianca is None


def test_referencia_exata_equilibrada_nao_e_deslocada_por_otimizacao_numerica():
    energia = (9.0, 82.0, 15.0, 4.0, 0.03, 0.25)
    proteico = (49.0, 81.0, 15.0, 2.0, 0.33, 0.57)
    contexto = ContextoZootecnico("cordeiros_4_meses", "crescimento", 30.0, 0.3, 1.0)
    referencia = ReferenciaSuplemento(
        contexto=contexto, pb=16.0, ndt=70.0, ca=0.4, p=0.3, ca_p=1.3,
        receita=(0.70, 0.30), codigo="TESTE-PRESERVACAO",
        ingredientes=(
            IngredienteReferencia("CONCENTRADO", "ENERGETICO", 0.70, energia),
            IngredienteReferencia("CONCENTRADO", "PROTEICO", 0.30, proteico),
        ),
    )
    resultado = MotorAdequacao.gerar_distribuicao_inicial(
        matriz_M=np.array([[*energia, 0.0], [*proteico, 0.0]]),
        requisitos=_requisitos(),
        configuracoes=[
            ConfiguracaoIngrediente("CONCENTRADO", tipo="ENERGETICO"),
            ConfiguracaoIngrediente("CONCENTRADO", tipo="PROTEICO"),
        ],
        percentual_alvo_volumoso=0.0,
        contexto_zootecnico=contexto,
        referencias_suplemento=(referencia,),
    )

    assert resultado.convergiu
    assert resultado.fracoes == pytest.approx([0.70, 0.30])
    assert resultado.origem_alvo == "referencia_validada_exata:TESTE-PRESERVACAO"


def test_cenario_proximo_usa_preferencia_aprendida_sem_virar_referencia_exata():
    energia = (9.0, 84.0, 14.0, 4.0, 0.03, 0.25)
    proteico = (48.0, 80.0, 15.0, 2.0, 0.33, 0.57)
    referencias = []
    for indice in range(9):
        pb = 10.0 + indice * 2.0
        participacao_proteico = 0.10 + indice * 0.04
        referencias.append(ReferenciaSuplemento(
            contexto=ContextoZootecnico(
                "cordeiros_4_meses", "crescimento", 20.0 + indice * 5.0,
                0.20 + indice * 0.01, 0.60 + indice * 0.05,
            ),
            pb=pb, ndt=70.0, ca=0.4, p=0.3, ca_p=1.3,
            receita=(1.0 - participacao_proteico, participacao_proteico),
            codigo=f"GUIA-APRENDIDA-{indice}",
            ingredientes=(
                IngredienteReferencia("CONCENTRADO", "ENERGETICO", 1.0 - participacao_proteico, energia),
                IngredienteReferencia("CONCENTRADO", "PROTEICO", participacao_proteico, proteico),
            ),
        ))
    requisitos = _requisitos()
    requisitos[Nutriente.PB] = RequisitoNutriente.maior_igual(
        Nutriente.PB, 17.0, valor_origem_nrc=17.0
    )

    _, exata, origem, confianca = MotorAdequacao._preparar_x_alvo(
        configuracoes=[
            ConfiguracaoIngrediente("CONCENTRADO", tipo="ENERGETICO"),
            ConfiguracaoIngrediente("CONCENTRADO", tipo="PROTEICO"),
        ],
        percentual_volumoso=0.0,
        matriz_M=np.array([[*energia, 0.0], [*proteico, 0.0]]),
        requisitos=requisitos,
        contexto_zootecnico=ContextoZootecnico(
            "cordeiros_4_meses", "crescimento", 37.5, 0.235, 0.775
        ),
        referencias_suplemento=tuple(referencias),
    )

    assert not exata
    assert origem == "preferencia_aprendida"
    assert 0.20 <= confianca <= 0.49
