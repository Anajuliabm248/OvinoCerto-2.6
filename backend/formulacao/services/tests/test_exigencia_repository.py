from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Usuario
from exigencia_nrc.models import ExigenciaNRC
from formulacao.domain.nutrientes import Nutriente
from formulacao.domain.requisito import Operador
from formulacao.models import ConfiguracaoNutriente, Formulacao
from formulacao.repositories import ExigenciaRepository
from lote.models import Lote
from propriedade.models import Propriedade


class ExigenciaRepositoryPBPadraoTests(TestCase):
    def setUp(self):
        conta = get_user_model().objects.create_user(
            username="pb-ideal",
            password="senha-de-teste",
        )
        self.usuario = Usuario.objects.create(
            user=conta,
            nome="Usuário PB ideal",
            email="pb-ideal@example.com",
            cpf="98765432100",
            telefone="55999999998",
            estado="RS",
            cidade="Santa Maria",
            profissao="Produtor",
        )
        propriedade = Propriedade.objects.create(
            usuario=self.usuario,
            nome="Propriedade PB ideal",
            proprietario="Usuário PB ideal",
            uf="RS",
            cidade="Santa Maria",
            localidade="Interior",
        )
        self.lote = Lote.objects.create(
            propriedade=propriedade,
            nome_lote="Lote PB ideal",
            categoria="cordeiros_4_meses",
            fase="crescimento",
            peso_vivo=25.0,
            gmd_esperado=0.2,
            num_animais=10,
        )
        self.nrc = ExigenciaNRC.objects.create(
            categoria="cordeiros_4_meses",
            fase="crescimento",
            pv_kg=25.0,
            cms_kg=1.0,
            pb_percentual=18.0,
            ndt_percentual=70.0,
        )

    def _criar_formulacao(self, titulo: str) -> Formulacao:
        return Formulacao.objects.create(
            lote=self.lote,
            usuario=self.usuario,
            titulo=titulo,
        )

    def test_criar_de_nrc_persiste_pb_como_valor_ideal(self):
        formulacao = self._criar_formulacao("PB padrão igual")

        ExigenciaRepository.criar_de_nrc(formulacao, self.nrc, cms_kg=1.0)

        config = ConfiguracaoNutriente.objects.get(
            exigencia_configurada__formulacao=formulacao,
            nutriente="PB",
        )
        assert config.operador == "="
        assert config.valor_min == 18.0
        assert config.valor_max == 18.0
        assert config.valor_origem_nrc == 18.0
        assert config.alterado_pelo_usuario is False

        requisito = ExigenciaRepository.get_requisitos(formulacao.id)[Nutriente.PB]
        assert requisito.operador == Operador.IGUAL
        assert requisito.valor_min == 17.99
        assert requisito.valor_max == 18.01

    def test_migracao_converte_apenas_pb_nao_alterada_pelo_usuario(self):
        padrao = self._criar_formulacao("PB legada padrão")
        manual = self._criar_formulacao("PB legada manual")
        ExigenciaRepository.criar_de_nrc(padrao, self.nrc, cms_kg=1.0)
        ExigenciaRepository.criar_de_nrc(manual, self.nrc, cms_kg=1.0)
        ConfiguracaoNutriente.objects.filter(
            exigencia_configurada__formulacao=padrao,
            nutriente="PB",
        ).update(operador=">=", valor_min=18.0, valor_max=None)
        ConfiguracaoNutriente.objects.filter(
            exigencia_configurada__formulacao=manual,
            nutriente="PB",
        ).update(
            operador=">=",
            valor_min=20.0,
            valor_max=None,
            alterado_pelo_usuario=True,
        )

        migracao = import_module(
            "formulacao.migrations.0013_pb_padrao_como_valor_ideal"
        )
        migracao.definir_pb_padrao_como_igual(apps, None)

        pb_padrao = ConfiguracaoNutriente.objects.get(
            exigencia_configurada__formulacao=padrao,
            nutriente="PB",
        )
        pb_manual = ConfiguracaoNutriente.objects.get(
            exigencia_configurada__formulacao=manual,
            nutriente="PB",
        )
        assert (pb_padrao.operador, pb_padrao.valor_min, pb_padrao.valor_max) == (
            "=", 18.0, 18.0
        )
        assert (pb_manual.operador, pb_manual.valor_min, pb_manual.valor_max) == (
            ">=", 20.0, None
        )
