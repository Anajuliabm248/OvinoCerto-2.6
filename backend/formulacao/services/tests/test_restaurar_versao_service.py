from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Usuario
from exigencia_nrc.models import ExigenciaNRC
from formulacao.models import (
    ConfiguracaoNutriente,
    EventoFormulacao,
    ExigenciaConfigurada,
    Formulacao,
    IngredienteFormulacao,
    SnapshotFormulacao,
    TipoEvento,
)
from formulacao.services.atualizar_percentual_volumoso_service import (
    AtualizarPercentualVolumosoService,
)
from formulacao.services.restaurar_versao_service import RestaurarVersaoService
from ingrediente.models import Ingrediente
from lote.models import Lote
from propriedade.models import Propriedade


class RestaurarVersaoServiceTests(TestCase):
    def setUp(self):
        conta = get_user_model().objects.create_user(
            username="restauracao",
            password="senha-de-teste",
        )
        usuario = Usuario.objects.create(
            user=conta,
            nome="Usuário de teste",
            email="restauracao@example.com",
            cpf="12345678900",
            telefone="55999999999",
            estado="RS",
            cidade="Santa Maria",
            profissao="Produtor",
        )
        propriedade = Propriedade.objects.create(
            usuario=usuario,
            nome="Propriedade de teste",
            proprietario="Usuário de teste",
            uf="RS",
            cidade="Santa Maria",
            localidade="Interior",
        )
        lote = Lote.objects.create(
            propriedade=propriedade,
            nome_lote="Lote de teste",
            categoria="cordeiros_4_meses",
            fase="crescimento",
            peso_vivo=25.0,
            gmd_esperado=0.2,
            num_animais=10,
        )
        self.formulacao = Formulacao.objects.create(
            lote=lote,
            usuario=usuario,
            titulo="Formulação de teste",
        )
        self.origem_antiga = self._criar_nrc(20.0)
        origem_atual = self._criar_nrc(30.0)
        self.exigencia = ExigenciaConfigurada.objects.create(
            formulacao=self.formulacao,
            exigencia_nrc_origem=origem_atual,
            cms_kg=9.9,
        )
        ConfiguracaoNutriente.objects.create(
            exigencia_configurada=self.exigencia,
            nutriente="PB",
            operador=">=",
            valor_min=99.0,
            valor_max=None,
            valor_origem_nrc=99.0,
            alterado_pelo_usuario=True,
        )
        ConfiguracaoNutriente.objects.create(
            exigencia_configurada=self.exigencia,
            nutriente="NDT",
            operador=">=",
            valor_min=88.0,
            valor_max=None,
            valor_origem_nrc=88.0,
            alterado_pelo_usuario=True,
        )
        SnapshotFormulacao.objects.create(
            formulacao=self.formulacao,
            versao_num=1,
            payload={
                "participacoes": [{"id": 999, "fracao": 1.0}],
                "percentual_alvo_volumoso": 0.35,
                "exigencia_configurada": {
                    "cms_kg": 1.2,
                    "exigencia_nrc_origem_id": self.origem_antiga.id,
                    "configuracoes": [
                        {
                            "nutriente": "PB",
                            "operador": ">=",
                            "valor_min": 14.0,
                            "valor_max": None,
                            "valor_origem_nrc": 13.5,
                            "alterado_pelo_usuario": False,
                        },
                        {
                            "nutriente": "EE",
                            "operador": "<=",
                            "valor_min": None,
                            "valor_max": 6.0,
                            "valor_origem_nrc": 6.0,
                            "alterado_pelo_usuario": True,
                        },
                    ],
                },
            },
        )

    @staticmethod
    def _criar_nrc(pv_kg: float) -> ExigenciaNRC:
        return ExigenciaNRC.objects.create(
            categoria="cordeiros_4_meses",
            fase="crescimento",
            pv_kg=pv_kg,
        )

    def test_restaura_exigencias_do_snapshot_antes_do_recalculo(self):
        with patch(
            "formulacao.services.restaurar_versao_service."
            "RecalcularFormulacaoService.executar"
        ) as recalcular:
            RestaurarVersaoService.executar(
                formulacao_id=self.formulacao.id,
                versao_num=1,
            )

        self.exigencia.refresh_from_db()
        self.formulacao.refresh_from_db()
        assert self.exigencia.cms_kg == 1.2
        assert self.formulacao.percentual_alvo_volumoso == 0.35
        assert self.exigencia.exigencia_nrc_origem_id == self.origem_antiga.id

        configuracoes = {
            config.nutriente: config
            for config in self.exigencia.configuracoes_nutrientes.all()
        }
        assert set(configuracoes) == {"PB", "EE"}
        assert configuracoes["PB"].valor_min == 14.0
        assert configuracoes["PB"].valor_origem_nrc == 13.5
        assert configuracoes["PB"].alterado_pelo_usuario is False
        assert configuracoes["EE"].operador == "<="
        assert configuracoes["EE"].valor_max == 6.0
        assert configuracoes["EE"].alterado_pelo_usuario is True

        recalcular.assert_called_once_with(
            formulacao_id=self.formulacao.id,
            usuario_id=None,
            motivo="restauração da versão 1",
        )
        evento = EventoFormulacao.objects.get(tipo_evento=TipoEvento.VERSAO_RESTAURADA)
        assert evento.payload["exigencias_restauradas"] is True

    def test_atualizar_percentual_volumoso_redistribui_e_audita_sem_geracao_inicial(self):
        volumoso = self._criar_ingrediente("Volumoso", "volumoso", "silagens")
        concentrado_a = self._criar_ingrediente("Concentrado A", "concentrado", "energetico")
        concentrado_b = self._criar_ingrediente("Concentrado B", "concentrado", "proteico")
        IngredienteFormulacao.objects.create(
            formulacao=self.formulacao,
            ingrediente=volumoso,
            ms_porcent=20.0,
        )
        IngredienteFormulacao.objects.create(
            formulacao=self.formulacao,
            ingrediente=concentrado_a,
            ms_porcent=40.0,
        )
        IngredienteFormulacao.objects.create(
            formulacao=self.formulacao,
            ingrediente=concentrado_b,
            ms_porcent=40.0,
        )

        with patch(
            "formulacao.services.atualizar_percentual_volumoso_service."
            "RecalcularFormulacaoService.executar"
        ) as recalcular:
            AtualizarPercentualVolumosoService.executar(
                formulacao_id=self.formulacao.id,
                percentual_alvo_volumoso=0.40,
            )

        self.formulacao.refresh_from_db()
        participacao_volumoso = IngredienteFormulacao.objects.get(
            formulacao=self.formulacao,
            ingrediente=volumoso,
        ).ms_porcent
        assert self.formulacao.percentual_alvo_volumoso == 0.40
        assert participacao_volumoso == 40.0
        recalcular.assert_called_once()
        evento = EventoFormulacao.objects.get(
            tipo_evento=TipoEvento.PERCENTUAL_VOLUMOSO_ALTERADO
        )
        assert evento.payload["percentual_anterior"] == 0.50
        assert evento.payload["percentual_novo"] == 0.40

    @staticmethod
    def _criar_ingrediente(nome: str, classificacao: str, tipo: str) -> Ingrediente:
        return Ingrediente.objects.create(
            nome=nome,
            classificacao=classificacao,
            tipo=tipo,
            ms=90.0,
            pb=15.0,
            ndt=70.0,
            fdn=30.0,
            ee=2.0,
            ca=0.5,
            p=0.4,
            fonte_valadares=True,
        )
