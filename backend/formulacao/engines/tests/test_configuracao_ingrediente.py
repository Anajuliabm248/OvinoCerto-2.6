"""
pytest formulacao/services/tests/test_configuracao_ingrediente.py -v

configuracao_a_partir_do_ingrediente() só lê atributos do model
Ingrediente — não precisa gravar no banco, então as instâncias abaixo
nunca são salvas (.save() não é chamado).
"""

from formulacao.services._configuracao_ingrediente import configuracao_a_partir_do_ingrediente
from ingrediente.models import Ingrediente


def _ingrediente(classificacao="concentrado", limite=None, limite_min=None):
    return Ingrediente(
        classificacao=classificacao,
        tipo="mineral",
        nome="Bicarbonato de sódio",
        ms=99.0, pb=0.0, ndt=0.0, fdn=0.0, ee=0.0, ca=0.0, p=0.0,
        limite_min_participacao=limite_min,
        limite_max_participacao=limite,
    )


class TestConfiguracaoAPartirDoIngrediente:

    def test_sem_limite_configurado_usa_100_por_cento(self):
        cfg = configuracao_a_partir_do_ingrediente(_ingrediente(limite=None))
        assert cfg.limite_max == 1.0
        assert cfg.limite_min == 0.0

    def test_ingrediente_none_usa_100_por_cento_e_concentrado(self):
        cfg = configuracao_a_partir_do_ingrediente(None)
        assert cfg.limite_max == 1.0
        assert cfg.classificacao == "CONCENTRADO"

    def test_converte_percentual_cadastrado_para_fracao(self):
        cfg = configuracao_a_partir_do_ingrediente(_ingrediente(limite=1.5))
        assert cfg.limite_max == 0.015

    def test_converte_minimo_cadastrado_para_fracao(self):
        cfg = configuracao_a_partir_do_ingrediente(
            _ingrediente(limite=5.0, limite_min=1.5)
        )
        assert cfg.limite_min == 0.015
        assert cfg.limite_max == 0.05

    def test_classificacao_e_normalizada_para_maiusculo(self):
        cfg = configuracao_a_partir_do_ingrediente(_ingrediente(classificacao="volumoso"))
        assert cfg.classificacao == "VOLUMOSO"

    def test_tipo_e_repassado_normalizado_para_o_motor(self):
        cfg = configuracao_a_partir_do_ingrediente(_ingrediente())
        assert cfg.tipo == "MINERAL"

    def test_converte_preco_resolvido_para_custo_por_kg_de_ms(self):
        ingrediente = _ingrediente()
        cfg = configuracao_a_partir_do_ingrediente(
            ingrediente,
            custo_kg_mn=1.98,
        )
        assert cfg.custo_por_kg_ms == 2.0

    def test_preco_ausente_nao_e_convertido_em_custo_zero(self):
        cfg = configuracao_a_partir_do_ingrediente(_ingrediente())
        assert cfg.custo_por_kg_ms is None

    def test_respeita_limite_min_customizado(self):
        # limite_min=0.05 (5%), mas ingrediente cadastrado com limite de 2%:
        # o limite_max nunca pode ficar abaixo do limite_min.
        cfg = configuracao_a_partir_do_ingrediente(
            _ingrediente(limite=2.0), limite_min=0.05
        )
        assert cfg.limite_max >= cfg.limite_min
        assert cfg.limite_min == 0.05

    def test_limite_100_por_cento_fica_dentro_dos_bounds(self):
        cfg = configuracao_a_partir_do_ingrediente(_ingrediente(limite=100.0))
        assert cfg.limite_max == 1.0
