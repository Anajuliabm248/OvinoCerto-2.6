"""Contratos HTTP para a disponibilidade dos Quadros 12, 13 e 14."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Usuario
from exigencia_nrc.models import ExigenciaNRC
from formulacao.models import (
    ExigenciaConfigurada,
    Formulacao,
    IngredienteFormulacao,
    ParametrosViabilidade,
)
from ingrediente.models import Ingrediente
from lote.models import Lote
from propriedade.models import Propriedade


class ViabilidadeAPITests(APITestCase):
    """Protege a projeção econômica fora das exigências de cordeiros."""

    def setUp(self):
        conta = get_user_model().objects.create_user(
            "viabilidade@example.com",
            password="SenhaForte123!",
        )
        usuario = Usuario.objects.create(
            user=conta,
            nome="Usuário de viabilidade",
            email="viabilidade@example.com",
            cpf="99999999999",
            telefone="55999999999",
            estado="RS",
            cidade="Santa Maria",
            profissao="Produtor",
        )
        propriedade = Propriedade.objects.create(
            usuario=usuario,
            nome="Propriedade de teste",
            proprietario="Usuário de viabilidade",
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
        ingrediente = Ingrediente.objects.create(
            usuario=usuario,
            classificacao="volumoso",
            tipo="silagens",
            nome="Silagem de teste",
            ms=50.0,
            pb=8.0,
            ndt=60.0,
            fdn=50.0,
            ee=2.0,
            ca=0.3,
            p=0.2,
        )
        IngredienteFormulacao.objects.create(
            formulacao=self.formulacao,
            ingrediente=ingrediente,
            ms_porcent=100.0,
        )
        self.client.force_authenticate(conta)

    def _configurar_exigencia(
        self,
        categoria,
        fase="crescimento",
        pv_kg=25.0,
        cms_kg=1.0,
    ):
        origem = ExigenciaNRC.objects.create(
            categoria=categoria,
            fase=fase,
            pv_kg=pv_kg,
        )
        return ExigenciaConfigurada.objects.create(
            formulacao=self.formulacao,
            exigencia_nrc_origem=origem,
            cms_kg=cms_kg,
        )

    def _ajustar_lote(self, categoria, fase="crescimento"):
        lote = self.formulacao.lote
        lote.categoria = categoria
        lote.fase = fase
        lote.save(update_fields=["categoria", "fase"])

    def test_consulta_mantem_indices_e_custos_para_exigencia_nao_cordeiro(self):
        self._ajustar_lote("carneiro_4_meses")
        self._configurar_exigencia("carneiro_4_meses")

        resposta = self.client.get(
            reverse("formulacao-viabilidade", args=[self.formulacao.pk])
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertIn("indices", resposta.data)
        self.assertIn("linhas_custo", resposta.data)
        self.assertNotIn("preco_minimo_kg_pv", resposta.data)
        self.assertNotIn("resultado_animal", resposta.data)
        self.assertNotIn("resultado_lote", resposta.data)
        self.assertNotIn("preco_venda_kg_pv", resposta.data["parametros"])

    def test_preco_enviado_pelo_formulario_e_ignorado_para_nao_cordeiro(self):
        self._ajustar_lote("carneiro_4_meses")
        self._configurar_exigencia("carneiro_4_meses")

        resposta = self.client.patch(
            reverse(
                "formulacao-atualizar-parametros-viabilidade",
                args=[self.formulacao.pk],
            ),
            {"gmd_esperado_kg": 0.3, "preco_venda_kg_pv": 13.0},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["gmd_esperado_kg"], 0.3)
        self.assertNotIn("preco_venda_kg_pv", resposta.data)
        parametros = ParametrosViabilidade.objects.get(formulacao=self.formulacao)
        self.assertEqual(parametros.gmd_esperado_kg, 0.3)
        self.assertIsNone(parametros.preco_venda_kg_pv)

    def test_atualizacao_dos_indices_permanece_disponivel_para_nao_cordeiro(self):
        self._ajustar_lote("carneiro_4_meses")
        self._configurar_exigencia("carneiro_4_meses")

        resposta = self.client.patch(
            reverse(
                "formulacao-atualizar-parametros-viabilidade",
                args=[self.formulacao.pk],
            ),
            {"gmd_esperado_kg": 0.3},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["gmd_esperado_kg"], 0.3)
        self.assertNotIn("preco_venda_kg_pv", resposta.data)

    def test_preco_vazio_nao_bloqueia_patch_dos_indices_para_nao_cordeiro(self):
        self._ajustar_lote("carneiro_4_meses")
        self._configurar_exigencia("carneiro_4_meses")

        resposta = self.client.patch(
            reverse(
                "formulacao-atualizar-parametros-viabilidade",
                args=[self.formulacao.pk],
            ),
            {
                "gmd_esperado_kg": 0.3,
                "preco_venda_kg_pv": "",
            },
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["gmd_esperado_kg"], 0.3)
        parametros = ParametrosViabilidade.objects.get(formulacao=self.formulacao)
        self.assertEqual(parametros.gmd_esperado_kg, 0.3)

    def test_consulta_de_cordeiro_sem_preco_mantem_indices_e_custos(self):
        self._configurar_exigencia("cordeiros_4_meses")

        resposta = self.client.get(
            reverse("formulacao-viabilidade", args=[self.formulacao.pk])
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertIn("indices", resposta.data)
        self.assertIn("linhas_custo", resposta.data)
        self.assertIsNone(resposta.data["parametros"]["preco_venda_kg_pv"])
        self.assertNotIn("preco_minimo_kg_pv", resposta.data)
        self.assertNotIn("resultado_animal", resposta.data)

    def test_exigencia_incompativel_ignora_lote_e_converte_cms_em_percentual(self):
        self._configurar_exigencia(
            "ovelhas",
            fase="gestacao_tardia",
            pv_kg=70.0,
            cms_kg=2.1,
        )
        ParametrosViabilidade.objects.create(
            formulacao=self.formulacao,
            num_animais=10,
            gmd_esperado_kg=0.2,
            estimativa_permanencia_dias=60,
            peso_entrada_kg=25.0,
            cms_percentual_pv=0.04,
            perdas_alimentos_percentual=0.08,
        )

        resposta = self.client.get(
            reverse("formulacao-viabilidade", args=[self.formulacao.pk])
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertTrue(resposta.data["configuracao_pendente"])
        self.assertEqual(resposta.data["dados_animal"]["categoria"], "Ovelhas")
        self.assertEqual(resposta.data["dados_animal"]["peso_vivo_kg"], 70.0)
        self.assertEqual(resposta.data["parametros"]["num_animais"], 0)
        self.assertEqual(resposta.data["parametros"]["peso_entrada_kg"], 0.0)
        self.assertEqual(resposta.data["parametros"]["cms_percentual_pv"], 3.0)
        self.assertEqual(
            resposta.data["campos_pendentes"],
            ["num_animais", "peso_entrada_kg"],
        )

    def test_cms_ausente_nao_recebe_percentual_presumido(self):
        self._configurar_exigencia(categoria="cordeiros_4_meses", cms_kg=0.0)

        resposta = self.client.get(
            reverse("formulacao-viabilidade", args=[self.formulacao.pk])
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertTrue(resposta.data["configuracao_pendente"])
        self.assertEqual(resposta.data["parametros"]["cms_percentual_pv"], 0.0)
        self.assertEqual(resposta.data["campos_pendentes"], ["cms_percentual_pv"])

    def test_percentuais_da_api_sao_normalizados_para_o_motor(self):
        self._configurar_exigencia("cordeiros_4_meses")

        resposta = self.client.patch(
            reverse(
                "formulacao-atualizar-parametros-viabilidade",
                args=[self.formulacao.pk],
            ),
            {
                "cms_percentual_pv": 3.0,
                "perdas_alimentos_percentual": 8.0,
            },
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["cms_percentual_pv"], 3.0)
        self.assertEqual(resposta.data["perdas_alimentos_percentual"], 8.0)
        parametros = ParametrosViabilidade.objects.get(formulacao=self.formulacao)
        self.assertEqual(parametros.cms_percentual_pv, 0.03)
        self.assertEqual(parametros.perdas_alimentos_percentual, 0.08)

    def test_atualizacao_do_preco_de_venda_permanece_disponivel_para_cordeiro(self):
        self._configurar_exigencia("cordeiros_4_meses")

        resposta = self.client.patch(
            reverse(
                "formulacao-atualizar-parametros-viabilidade",
                args=[self.formulacao.pk],
            ),
            {"preco_venda_kg_pv": 13.0},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["preco_venda_kg_pv"], 13.0)

        consulta = self.client.get(
            reverse("formulacao-viabilidade", args=[self.formulacao.pk])
        )

        self.assertEqual(consulta.status_code, status.HTTP_200_OK)
        self.assertIn("preco_minimo_kg_pv", consulta.data)
        self.assertIn("resultado_animal", consulta.data)
        self.assertIn("resultado_lote", consulta.data)
