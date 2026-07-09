"""
pytest formulacao/engines/tests/test_motor_recalculo.py -v

Estes testes validam o pipeline completo do MotorRecalculo com
dados fictícios controlados, verificando:
- cálculo correto de % MS por nutriente
- cálculo correto de kg por ingrediente/dia
- identificação de DEFICIT / EXCESSO / ATENDE
- comportamento da mascara de travados em ParticipacaoVetor
- idempotência (mesma entrada, mesmo resultado)
"""

import numpy as np
import pytest

from formulacao.domain.nutrientes import Nutriente, NUTRIENTES_ORDEM
from formulacao.domain.participacao import OrigemParticipacao, ParticipacaoVetor
from formulacao.domain.requisito import RequisitoNutriente, StatusAdequacao, Operador
from formulacao.domain.resultado import ResultadoAdequacao
from formulacao.domain.vetor_nutricional import VetorNutricional
from formulacao.engines.motor_recalculo import EntradaRecalculo, MotorRecalculo


# Fixtures

def _vetor(pb=0.0, ndt=0.0, fdn=0.0, ee=0.0, ca=0.0, p=0.0) -> VetorNutricional:
    """Cria VetorNutricional por keyword — conveniência nos testes."""
    return VetorNutricional.from_dict({"PB": pb, "NDT": ndt, "FDN": fdn,
                                        "EE": ee, "CA": ca, "P": p})


def _participacao(ids, fracoes, origens=None) -> ParticipacaoVetor:
    if origens is None:
        origens = [OrigemParticipacao.CALCULADA] * len(ids)
    return ParticipacaoVetor(
        ids_ingredientes=tuple(ids),
        fracoes=np.array(fracoes, dtype=float),
        origens=tuple(origens),
    )


def _requisitos_basicos() -> dict[Nutriente, RequisitoNutriente]:
    return {
        Nutriente.PB: RequisitoNutriente.maior_igual(Nutriente.PB, 16.0),
        Nutriente.NDT: RequisitoNutriente.maior_igual(Nutriente.NDT, 60.0),
        Nutriente.FDN: RequisitoNutriente.menor_igual(Nutriente.FDN, 40.0),
        Nutriente.EE: RequisitoNutriente.maior_igual(Nutriente.EE, 2.0),
        Nutriente.CA: RequisitoNutriente.entre(Nutriente.CA, 0.2, 0.8),
        Nutriente.P: RequisitoNutriente.entre(Nutriente.P, 0.15, 0.5),
    }



# Testes: VetorNutricional


class TestVetorNutricional:

    def test_from_dict_valores_corretos(self):
        v = _vetor(pb=18.5, ndt=70.0, fdn=35.0, ee=3.0, ca=0.4, p=0.25)
        assert v.get(Nutriente.PB) == pytest.approx(18.5)
        assert v.get(Nutriente.NDT) == pytest.approx(70.0)
        assert v.get(Nutriente.FDN) == pytest.approx(35.0)

    def test_nutriente_ausente_assume_zero(self):
        v = VetorNutricional.from_dict({"PB": 20.0})
        assert v.get(Nutriente.NDT) == pytest.approx(0.0)

    def test_multiplicacao_por_escalar(self):
        v = _vetor(pb=20.0, ndt=60.0)
        r = v * 0.5
        assert r.get(Nutriente.PB) == pytest.approx(10.0)
        assert r.get(Nutriente.NDT) == pytest.approx(30.0)

    def test_soma_de_vetores(self):
        v1 = _vetor(pb=10.0, ndt=30.0)
        v2 = _vetor(pb=5.0, ndt=20.0)
        r = v1 + v2
        assert r.get(Nutriente.PB) == pytest.approx(15.0)
        assert r.get(Nutriente.NDT) == pytest.approx(50.0)

    def test_shape_errado_levanta_erro(self):
        with pytest.raises(ValueError, match="shape"):
            VetorNutricional(valores=np.array([1.0, 2.0]))  # shape (2,) != (6,)



# Testes: RequisitoNutriente


class TestRequisitoNutriente:

    def test_maior_igual_deficit(self):
        r = RequisitoNutriente.maior_igual(Nutriente.PB, 16.0)
        status, mag = r.avaliar(14.0)
        assert status == StatusAdequacao.DEFICIT
        assert mag == pytest.approx(2.0 / 16.0)

    def test_maior_igual_atende(self):
        r = RequisitoNutriente.maior_igual(Nutriente.PB, 16.0)
        status, _ = r.avaliar(18.0)
        assert status == StatusAdequacao.ATENDE

    def test_menor_igual_excesso(self):
        r = RequisitoNutriente.menor_igual(Nutriente.FDN, 40.0)
        status, mag = r.avaliar(50.0)
        assert status == StatusAdequacao.EXCESSO
        assert mag == pytest.approx(10.0 / 40.0)

    def test_entre_atende(self):
        r = RequisitoNutriente.entre(Nutriente.CA, 0.2, 0.8)
        status, _ = r.avaliar(0.5)
        assert status == StatusAdequacao.ATENDE

    def test_entre_deficit(self):
        r = RequisitoNutriente.entre(Nutriente.CA, 0.2, 0.8)
        status, _ = r.avaliar(0.1)
        assert status == StatusAdequacao.DEFICIT

    def test_igual_usa_tolerancia(self):
        r = RequisitoNutriente.igual(Nutriente.PB, 16.0)
        # valor_min e valor_max diferem por 2 * TOLERANCIA_IGUALDADE
        assert r.valor_min == pytest.approx(16.0 - 0.01)
        assert r.valor_max == pytest.approx(16.0 + 0.01)

    def test_entre_min_maior_max_levanta_erro(self):
        with pytest.raises(ValueError, match="valor_min < valor_max"):
            RequisitoNutriente.entre(Nutriente.CA, 0.8, 0.2)

    def test_limites_lp_maior_igual(self):
        r = RequisitoNutriente.maior_igual(Nutriente.PB, 16.0)
        lo, hi = r.limites_lp()
        assert lo == pytest.approx(16.0)
        assert hi is None

    def test_limites_lp_menor_igual(self):
        r = RequisitoNutriente.menor_igual(Nutriente.FDN, 40.0)
        lo, hi = r.limites_lp()
        assert lo is None
        assert hi == pytest.approx(40.0)



# Testes: ParticipacaoVetor


class TestParticipacaoVetor:

    def test_soma_correta(self):
        p = _participacao([1, 2, 3], [0.55, 0.30, 0.15])
        assert p.soma() == pytest.approx(1.0)
        assert p.soma_valida()

    def test_soma_invalida(self):
        p = _participacao([1, 2], [0.60, 0.60])  # soma = 1.2
        assert not p.soma_valida()

    def test_mascara_travados(self):
        p = _participacao(
            [1, 2, 3],
            [0.50, 0.30, 0.20],
            origens=[
                OrigemParticipacao.MANUAL_TRAVADA,
                OrigemParticipacao.CALCULADA,
                OrigemParticipacao.CALCULADA,
            ],
        )
        mascara = p.mascara_travados()
        assert mascara.tolist() == [True, False, False]
        assert p.soma_travados() == pytest.approx(0.50)
        assert p.espaco_livre() == pytest.approx(0.50)

    def test_escala_errada_levanta_erro(self):
        # fracoes em 0-100 em vez de 0-1 devem ser rejeitadas
        with pytest.raises(ValueError, match="0-100"):
            _participacao([1, 2], [55.0, 45.0])

    def test_com_origem_retorna_nova_instancia(self):
        p = _participacao([1, 2], [0.6, 0.4])
        p2 = p.com_origem(1, OrigemParticipacao.MANUAL_TRAVADA)
        assert p2.origens[0] == OrigemParticipacao.MANUAL_TRAVADA
        assert p.origens[0] == OrigemParticipacao.CALCULADA  # original intacto

    def test_com_fracoes_retorna_nova_instancia(self):
        p = _participacao([1, 2], [0.6, 0.4])
        p2 = p.com_fracoes(np.array([0.7, 0.3]))
        assert p2.fracoes[0] == pytest.approx(0.7)
        assert p.fracoes[0] == pytest.approx(0.6)  # original intacto



# Testes: MotorRecalculo


class TestMotorRecalculo:
    """
    Cenário base:
    - 2 ingredientes
    - Silagem de milho: PB=7%, NDT=65%, FDN=55%, EE=3%, CA=0.2%, P=0.15%
    - Farelo de soja:   PB=45%, NDT=78%, FDN=15%, EE=2%, CA=0.3%, P=0.65%
    - Participações: 60% silagem, 40% farelo
    - CMS: 1.0 kg/dia (facilita verificação manual)

    Esperado (% da MS):
      PB  = 0.60*7  + 0.40*45  = 4.2  + 18.0 = 22.2
      NDT = 0.60*65 + 0.40*78  = 39.0 + 31.2 = 70.2
      FDN = 0.60*55 + 0.40*15  = 33.0 + 6.0  = 39.0
      EE  = 0.60*3  + 0.40*2   = 1.8  + 0.8  = 2.6
      CA  = 0.60*0.2+ 0.40*0.3 = 0.12 + 0.12 = 0.24
      P   = 0.60*0.15+0.40*0.65= 0.09 + 0.26 = 0.35
    """

    def _entrada(self, cms_kg=1.0):
        silagem = _vetor(pb=7.0,  ndt=65.0, fdn=55.0, ee=3.0,  ca=0.20, p=0.15)
        farelo  = _vetor(pb=45.0, ndt=78.0, fdn=15.0, ee=2.0,  ca=0.30, p=0.65)
        M = MotorRecalculo.montar_matriz([silagem, farelo])
        participacao = _participacao([1, 2], [0.60, 0.40])
        return EntradaRecalculo(
            participacao=participacao,
            matriz_M=M,
            requisitos=_requisitos_basicos(),
            cms_kg=cms_kg,
        )

    def test_vetor_total_pct(self):
        saida = MotorRecalculo.calcular(self._entrada())
        vt = saida.vetor_total
        assert vt.get(Nutriente.PB)  == pytest.approx(22.2)
        assert vt.get(Nutriente.NDT) == pytest.approx(70.2)
        assert vt.get(Nutriente.FDN) == pytest.approx(39.0)
        assert vt.get(Nutriente.EE)  == pytest.approx(2.6)
        assert vt.get(Nutriente.CA)  == pytest.approx(0.24)
        assert vt.get(Nutriente.P)   == pytest.approx(0.35)
        assert vt.get(Nutriente.CA_P) == pytest.approx(0.24 / 0.35)

    def test_ms_kg_ingredientes(self):
        saida = MotorRecalculo.calcular(self._entrada(cms_kg=2.0))
        assert saida.ms_kg_ingredientes[0] == pytest.approx(1.2)  # 60% * 2kg
        assert saida.ms_kg_ingredientes[1] == pytest.approx(0.8)  # 40% * 2kg

    def test_contribuicoes_kg_pb(self):
        saida = MotorRecalculo.calcular(self._entrada(cms_kg=1.0))
        # PB da silagem: 0.60 kg * 7% / 100 = 0.042 kg
        assert saida.contribuicoes_kg[0, NUTRIENTES_ORDEM.index(Nutriente.PB)] == pytest.approx(0.042)
        # PB do farelo: 0.40 kg * 45% / 100 = 0.180 kg
        assert saida.contribuicoes_kg[1, NUTRIENTES_ORDEM.index(Nutriente.PB)] == pytest.approx(0.180)

    def test_resultado_atende_pb(self):
        # PB = 22.2% >= requisito de 16% -> ATENDE
        saida = MotorRecalculo.calcular(self._entrada())
        d = saida.resultado.desvio_de(Nutriente.PB)
        assert d.status == StatusAdequacao.ATENDE

    def test_resultado_atende_fdn(self):
        # FDN = 39.0% <= requisito de 40% -> ATENDE
        saida = MotorRecalculo.calcular(self._entrada())
        d = saida.resultado.desvio_de(Nutriente.FDN)
        assert d.status == StatusAdequacao.ATENDE

    def test_resultado_deficit_simulado(self):
        """Altera participação para forçar PB abaixo de 16%."""
        silagem = _vetor(pb=7.0,  ndt=65.0, fdn=55.0, ee=3.0, ca=0.20, p=0.15)
        farelo  = _vetor(pb=45.0, ndt=78.0, fdn=15.0, ee=2.0, ca=0.30, p=0.65)
        M = MotorRecalculo.montar_matriz([silagem, farelo])
        # 90% silagem + 10% farelo -> PB = 0.90*7 + 0.10*45 = 6.3+4.5 = 10.8% (< 16%)
        participacao = _participacao([1, 2], [0.90, 0.10])
        entrada = EntradaRecalculo(
            participacao=participacao,
            matriz_M=M,
            requisitos=_requisitos_basicos(),
            cms_kg=1.0,
        )
        saida = MotorRecalculo.calcular(entrada)
        d = saida.resultado.desvio_de(Nutriente.PB)
        assert d.status == StatusAdequacao.DEFICIT
        assert saida.resultado.em_deficit()

    def test_idempotencia(self):
        """Mesma entrada produz resultado idêntico em duas chamadas."""
        entrada = self._entrada()
        saida1 = MotorRecalculo.calcular(entrada)
        saida2 = MotorRecalculo.calcular(entrada)
        np.testing.assert_array_almost_equal(
            saida1.vetor_total.valores,
            saida2.vetor_total.valores,
        )

    def test_soma_valida(self):
        saida = MotorRecalculo.calcular(self._entrada())
        assert saida.resultado.soma_valida is True

    def test_montar_matriz_shape(self):
        vetores = [_vetor(pb=10.0), _vetor(pb=20.0), _vetor(pb=30.0)]
        M = MotorRecalculo.montar_matriz(vetores)
        assert M.shape == (3, len(NUTRIENTES_ORDEM))

    def test_montar_matriz_vazia(self):
        M = MotorRecalculo.montar_matriz([])
        assert M.shape == (0, len(NUTRIENTES_ORDEM))

    def test_cms_zero_levanta_erro(self):
        entrada_invalida = dict(
            participacao=_participacao([1], [1.0]),
            matriz_M=MotorRecalculo.montar_matriz([_vetor(pb=10.0)]),
            requisitos=_requisitos_basicos(),
            cms_kg=0.0,
        )
        with pytest.raises(ValueError, match="cms_kg"):
            EntradaRecalculo(**entrada_invalida)

    def test_resultado_to_dict_tem_schema_version(self):
        saida = MotorRecalculo.calcular(self._entrada())
        d = saida.resultado.to_dict()
        assert "schema_version" in d
        assert d["schema_version"] == 1
        assert "desvios" in d
        assert len(d["desvios"]) == len(_requisitos_basicos())
