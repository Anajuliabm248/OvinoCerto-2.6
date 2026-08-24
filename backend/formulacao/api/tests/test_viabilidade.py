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
    ParametrosViabilidade,
)
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
        self.client.force_authenticate(conta)

    def _configurar_exigencia(self, categoria):
        origem = ExigenciaNRC.objects.create(
            categoria=categoria,
            fase="crescimento",
            pv_kg=25.0,
        )
        return ExigenciaConfigurada.objects.create(
            formulacao=self.formulacao,
            exigencia_nrc_origem=origem,
            cms_kg=1.0,
        )

    def test_consulta_nao_expoe_quadros_economicos_para_exigencia_nao_cordeiro(self):
        self._configurar_exigencia("carneiro_4_meses")

        resposta = self.client.get(
            reverse("formulacao-viabilidade", args=[self.formulacao.pk])
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            resposta.data["detail"],
            "A viabilidade econômica (Quadros 12, 13 e 14) está disponível "
            "somente para exigências nutricionais de cordeiros.",
        )
        self.assertFalse(
            ParametrosViabilidade.objects.filter(formulacao=self.formulacao).exists()
        )

    def test_atualizacao_do_preco_de_venda_e_bloqueada_para_nao_cordeiro(self):
        self._configurar_exigencia("carneiro_4_meses")

        resposta = self.client.patch(
            reverse(
                "formulacao-atualizar-parametros-viabilidade",
                args=[self.formulacao.pk],
            ),
            {"preco_venda_kg_pv": 13.0},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            ParametrosViabilidade.objects.filter(formulacao=self.formulacao).exists()
        )

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
