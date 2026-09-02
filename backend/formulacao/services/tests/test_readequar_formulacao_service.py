"""Regressão da readequação explícita após editar uma exigência."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Usuario
from formulacao.models import (
    ConfiguracaoNutriente,
    EventoFormulacao,
    ExigenciaConfigurada,
    Formulacao,
    IngredienteFormulacao,
    ModoPercentualVolumoso,
    OrigemParticipacaoChoices,
    OrigemPercentualVolumoso,
    TipoEvento,
)
from formulacao.services.atualizar_exigencia_service import (
    AtualizarExigenciaService,
)
from ingrediente.models import Ingrediente
from lote.models import Lote
from propriedade.models import Propriedade

# pylint: disable=no-member


class ReadequarFormulacaoServiceTests(TestCase):
    """Valida a rota completa sem permitir que o motor rompa travas."""

    def setUp(self):
        self.conta = get_user_model().objects.create_user(
            username="readequacao",
            password="senha-de-teste",
        )
        self.usuario = Usuario.objects.create(
            user=self.conta,
            nome="Usuário de teste",
            email="readequacao@example.com",
            cpf="12345678900",
            telefone="55999999999",
            estado="RS",
            cidade="Santa Maria",
            profissao="Produtor",
        )
        propriedade = Propriedade.objects.create(
            usuario=self.usuario,
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
            usuario=self.usuario,
            titulo="Formulação para readequar",
            modo_percentual_volumoso=(
                ModoPercentualVolumoso.OTIMIZADO_PELO_SISTEMA
            ),
            percentual_alvo_volumoso=None,
            percentual_volumoso_aplicado=0.0,
            origem_percentual_volumoso=OrigemPercentualVolumoso.SISTEMA,
        )
        exigencia = ExigenciaConfigurada.objects.create(
            formulacao=self.formulacao,
            cms_kg=1.0,
        )
        ConfiguracaoNutriente.objects.create(
            exigencia_configurada=exigencia,
            nutriente="PB",
            operador=">=",
            valor_min=12.0,
            valor_origem_nrc=12.0,
            alterado_pelo_usuario=False,
        )

        ingrediente_travado = self._criar_ingrediente("Ingrediente travado", 10.0)
        ingrediente_energetico = self._criar_ingrediente("Ingrediente energético", 8.0)
        ingrediente_proteico = self._criar_ingrediente("Ingrediente proteico", 30.0)

        self.linha_travada = IngredienteFormulacao.objects.create(
            formulacao=self.formulacao,
            ingrediente=ingrediente_travado,
            ms_porcent=20.0,
            origem_participacao=OrigemParticipacaoChoices.MANUAL_TRAVADA,
        )
        self.linha_energetica = IngredienteFormulacao.objects.create(
            formulacao=self.formulacao,
            ingrediente=ingrediente_energetico,
            ms_porcent=60.0,
        )
        self.linha_proteica = IngredienteFormulacao.objects.create(
            formulacao=self.formulacao,
            ingrediente=ingrediente_proteico,
            ms_porcent=20.0,
        )

    @staticmethod
    def _criar_ingrediente(nome: str, pb: float) -> Ingrediente:
        """Cria um ingrediente mínimo com composição válida para o motor."""
        return Ingrediente.objects.create(
            classificacao="concentrado",
            tipo="proteico" if pb > 20.0 else "energetico",
            nome=nome,
            ms=90.0,
            pb=pb,
            ndt=70.0,
            fdn=15.0,
            ee=3.0,
            ca=0.6,
            p=0.3,
            custo_kg=1.0,
            fonte_valadares=True,
        )

    def test_usa_exigencia_vigente_e_redistribui_sem_alterar_trava(self):
        """O POST recalcular usa a meta editada e preserva soma e trava."""
        AtualizarExigenciaService.executar(
            formulacao_id=self.formulacao.id,
            nutriente="PB",
            operador=">=",
            valor=18.0,
            usuario_id=self.usuario.id,
        )
        self.linha_proteica.refresh_from_db()
        self.assertAlmostEqual(self.linha_proteica.ms_porcent, 20.0, places=8)

        self.client.force_login(self.conta)
        resposta = self.client.post(
            reverse("formulacao-recalcular", kwargs={"pk": self.formulacao.id})
        )
        self.assertEqual(resposta.status_code, 200, resposta.content)

        self.linha_travada.refresh_from_db()
        self.linha_energetica.refresh_from_db()
        self.linha_proteica.refresh_from_db()

        self.assertAlmostEqual(self.linha_travada.ms_porcent, 20.0, places=8)
        self.assertGreater(self.linha_proteica.ms_porcent, 0.0)
        soma = (
            self.linha_travada.ms_porcent
            + self.linha_energetica.ms_porcent
            + self.linha_proteica.ms_porcent
        )
        self.assertAlmostEqual(soma, 100.0, places=6)

        pb_total = (
            self.linha_travada.ms_porcent * 10.0
            + self.linha_energetica.ms_porcent * 8.0
            + self.linha_proteica.ms_porcent * 30.0
        ) / 100.0
        self.assertGreaterEqual(pb_total, 18.0 - 1e-6)
        self.assertTrue(
            EventoFormulacao.objects.filter(
                formulacao=self.formulacao,
                tipo_evento=TipoEvento.REDISTRIBUICAO_EXECUTADA,
            ).exists()
        )
