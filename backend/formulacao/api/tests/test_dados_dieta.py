"""Contrato autenticado e ausência de efeitos colaterais em Dados da Dieta."""

# pylint: disable=no-member, too-many-instance-attributes, missing-function-docstring

from copy import deepcopy

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Usuario
from formulacao.models import (
    EventoFormulacao,
    Formulacao,
    IngredienteFormulacao,
    SnapshotFormulacao,
)
from ingrediente.models import Ingrediente
from lote.models import Lote
from propriedade.models import Propriedade


NUTRIENTES = ("PB", "NDT", "FDN", "EE", "CA", "P", "CA_P")


class DadosDietaAPITests(APITestCase):
    """Protege propriedade, snapshot, unidades e imutabilidade do endpoint."""

    def setUp(self):
        self.conta, self.usuario = self._criar_usuario(
            "dados@example.com",
            "11111111111",
        )
        self.outra_conta, _ = self._criar_usuario(
            "outro@example.com",
            "22222222222",
        )
        propriedade = Propriedade.objects.create(
            usuario=self.usuario,
            nome="Propriedade",
            proprietario="Usuário",
            uf="RS",
            cidade="Santa Maria",
            localidade="Interior",
        )
        lote = Lote.objects.create(
            propriedade=propriedade,
            nome_lote="Lote",
            categoria="cordeiros_4_meses",
            fase="crescimento",
            peso_vivo=25.0,
            gmd_esperado=0.2,
            num_animais=10,
        )
        self.formulacao = Formulacao.objects.create(
            lote=lote,
            usuario=self.usuario,
            titulo="Dieta de teste",
            custo_mn_kg=1.25,
            custo_ms_kg=2.5,
            custo_animal_dia=3.0,
            custo_lote_dia=30.0,
        )
        volumoso = self._criar_ingrediente("volumoso", "Silagem", 50.0)
        concentrado = self._criar_ingrediente("concentrado", "Farelo", 80.0)
        concentrado_zero = self._criar_ingrediente(
            "concentrado",
            "Ureia selecionada",
            99.0,
        )
        self.volumoso_linha = IngredienteFormulacao.objects.create(
            formulacao=self.formulacao,
            ingrediente=volumoso,
            ms_porcent=50.0,
            ms_kg=1.0,
            mn_kg=2.0,
            custo_dia=0.0,
        )
        self.concentrado_linha = IngredienteFormulacao.objects.create(
            formulacao=self.formulacao,
            ingrediente=concentrado,
            ms_porcent=50.0,
            ms_kg=1.0,
            mn_kg=1.25,
            custo_kg_mn_override=2.0,
            origem_custo="OVERRIDE_LOCAL",
            custo_dia=2.5,
        )
        self.concentrado_zero_linha = IngredienteFormulacao.objects.create(
            formulacao=self.formulacao,
            ingrediente=concentrado_zero,
            ms_porcent=0.0,
            ms_kg=0.0,
            mn_kg=0.0,
            custo_dia=0.0,
        )
        SnapshotFormulacao.objects.create(
            formulacao=self.formulacao,
            versao_num=1,
            payload=self._snapshot_payload(pb=12.0),
        )
        SnapshotFormulacao.objects.create(
            formulacao=self.formulacao,
            versao_num=2,
            payload=self._snapshot_payload(pb=18.0),
        )
        self.url = reverse("formulacao-dados-dieta", args=[self.formulacao.pk])
        self.client.force_authenticate(self.conta)

    @staticmethod
    def _criar_usuario(email, cpf):
        conta = get_user_model().objects.create_user(
            email,
            password="SenhaForte123!",
        )
        usuario = Usuario.objects.create(
            user=conta,
            nome=email,
            email=email,
            cpf=cpf,
            telefone="55999999999",
            estado="RS",
            cidade="Santa Maria",
            profissao="Produtor",
        )
        return conta, usuario

    def _criar_ingrediente(self, classificacao, nome, ms):
        return Ingrediente.objects.create(
            usuario=self.usuario,
            classificacao=classificacao,
            tipo="silagens" if classificacao == "volumoso" else "energetico",
            nome=nome,
            ms=ms,
            pb=18.0,
            ndt=70.0,
            fdn=30.0,
            ee=3.0,
            ca=0.6,
            p=0.3,
        )

    @staticmethod
    def _snapshot_payload(pb):
        valores = {
            "PB": pb,
            "NDT": 70.0,
            "FDN": 30.0,
            "EE": 3.0,
            "CA": 0.6,
            "P": 0.3,
            "CA_P": 2.0,
        }
        operadores = {
            "PB": (">=", 14.0, None),
            "NDT": ("ENTRE", 65.0, 75.0),
            "FDN": ("<=", None, 35.0),
        }
        configs = []
        desvios = []
        for nutriente in NUTRIENTES:
            operador, minimo, maximo = operadores.get(
                nutriente,
                ("=", valores[nutriente] - 0.01, valores[nutriente] + 0.01),
            )
            configs.append({
                "nutriente": nutriente,
                "operador": operador,
                "valor_min": minimo,
                "valor_max": maximo,
                "valor_origem_nrc": valores[nutriente],
                "alterado_pelo_usuario": nutriente == "NDT",
            })
            desvios.append({
                "nutriente": nutriente,
                "valor_atual": valores[nutriente],
                "operador": operador,
                "valor_min": minimo,
                "valor_max": maximo,
                "alterado_pelo_usuario": nutriente == "NDT",
                "status": "ATENDE" if nutriente != "PB" or pb >= 14 else "DEFICIT",
                "magnitude_relativa": 0.0 if nutriente != "PB" or pb >= 14 else 0.1,
            })
        return {
            "vetor_total": valores,
            "resultado_adequacao": {
                "schema_version": 1,
                "soma_participacoes": 1.0,
                "soma_valida": True,
                "atende_tudo": pb >= 14,
                "desvios": desvios,
            },
            "exigencia_configurada": {
                "cms_kg": 2.0,
                "configuracoes": configs,
            },
        }

    def test_proprietario_recebe_os_quatro_blocos_do_ultimo_snapshot(self):
        resposta = self.client.get(self.url)

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["versao_num"], 2)
        self.assertIsNone(resposta.data["quantidade_mistura_mn_kg"])
        for bloco in (
            "dieta",
            "resumo_por_classificacao",
            "mistura_concentrada",
            "comparacao_nutricional",
        ):
            self.assertIn(bloco, resposta.data)
        self.assertEqual(
            resposta.data["comparacao_nutricional"]["composicao_dieta"]["PB"]["valor"],
            18.0,
        )
        self.assertEqual(
            resposta.data["comparacao_nutricional"]["versao_num"],
            2,
        )

    def test_outro_usuario_recebe_404(self):
        self.client.force_authenticate(self.outra_conta)

        resposta = self.client.get(self.url)

        self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)

    def test_quantidade_e_validada_e_fecha_exatamente_o_total_solicitado(self):
        resposta = self.client.get(
            self.url,
            {"quantidade_mistura_mn_kg": 4200},
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["quantidade_mistura_mn_kg"], 4200.0)
        self.assertEqual(
            resposta.data["mistura_concentrada"]["totais"]["mn_kg_para_quantidade"],
            4200.0,
        )
        for invalido in ("0", "-1", "abc", "inf"):
            erro = self.client.get(
                self.url,
                {"quantidade_mistura_mn_kg": invalido},
            )
            self.assertEqual(erro.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_persiste_quantidade_e_devolve_mistura_atualizada(self):
        """A escrita salva a quantidade e já retorna o total derivado solicitado."""
        snapshots_antes = SnapshotFormulacao.objects.filter(
            formulacao=self.formulacao
        ).count()
        eventos_antes = EventoFormulacao.objects.filter(
            formulacao=self.formulacao
        ).count()
        resposta = self.client.patch(
            self.url,
            {"quantidade_mistura_mn_kg": 4200},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.formulacao.refresh_from_db()
        self.assertEqual(self.formulacao.quantidade_mistura_mn_kg, 4200.0)
        self.assertEqual(resposta.data["quantidade_mistura_mn_kg"], 4200.0)
        self.assertEqual(
            resposta.data["mistura_concentrada"]["totais"][
                "mn_kg_para_quantidade"
            ],
            4200.0,
        )

        reaberta = self.client.get(self.url)
        self.assertEqual(reaberta.status_code, status.HTTP_200_OK)
        self.assertEqual(reaberta.data["quantidade_mistura_mn_kg"], 4200.0)

        editada = self.client.patch(
            self.url,
            {"quantidade_mistura_mn_kg": 3500},
            format="json",
        )
        self.assertEqual(editada.status_code, status.HTTP_200_OK)
        self.formulacao.refresh_from_db()
        self.assertEqual(self.formulacao.quantidade_mistura_mn_kg, 3500.0)
        detalhe = self.client.get(
            reverse("formulacao-detail", args=[self.formulacao.pk])
        )
        self.assertEqual(detalhe.data["quantidade_mistura_mn_kg"], 3500.0)
        self.assertEqual(
            SnapshotFormulacao.objects.filter(formulacao=self.formulacao).count(),
            snapshots_antes,
        )
        self.assertEqual(
            EventoFormulacao.objects.filter(formulacao=self.formulacao).count(),
            eventos_antes,
        )

    def test_query_override_nao_substitui_quantidade_persistida(self):
        """O contrato GET anterior continua momentâneo e retrocompatível."""
        self.formulacao.quantidade_mistura_mn_kg = 500.0
        self.formulacao.save(update_fields=["quantidade_mistura_mn_kg"])

        resposta = self.client.get(
            self.url,
            {"quantidade_mistura_mn_kg": 300},
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["quantidade_mistura_mn_kg"], 300.0)
        self.formulacao.refresh_from_db()
        self.assertEqual(self.formulacao.quantidade_mistura_mn_kg, 500.0)

    def test_patch_rejeita_quantidade_invalida_sem_alterar_valor_salvo(self):
        """Valores inválidos retornam 400 e preservam a última quantidade válida."""
        self.formulacao.quantidade_mistura_mn_kg = 500.0
        self.formulacao.save(update_fields=["quantidade_mistura_mn_kg"])

        for invalido in (0, -1, "abc", "inf"):
            resposta = self.client.patch(
                self.url,
                {"quantidade_mistura_mn_kg": invalido},
                format="json",
            )
            self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

        self.formulacao.refresh_from_db()
        self.assertEqual(self.formulacao.quantidade_mistura_mn_kg, 500.0)

    def test_patch_de_outro_usuario_nao_altera_quantidade(self):
        """A escrita usa a mesma proteção de propriedade do GET."""
        self.client.force_authenticate(self.outra_conta)

        resposta = self.client.patch(
            self.url,
            {"quantidade_mistura_mn_kg": 4200},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)
        self.formulacao.refresh_from_db()
        self.assertIsNone(self.formulacao.quantidade_mistura_mn_kg)

    def test_concentrado_com_zero_aparece_e_preco_ausente_e_explicito(self):
        resposta = self.client.get(self.url)

        linhas_mistura = resposta.data["mistura_concentrada"]["linhas"]
        zerada = next(
            linha for linha in linhas_mistura
            if linha["ing_form_id"] == self.concentrado_zero_linha.id
        )
        self.assertEqual(zerada["participacao_ms_mistura_percentual"], 0.0)
        self.assertEqual(zerada["mn_kg_por_100kg_mistura"], 0.0)
        linha_volumoso = next(
            linha for linha in resposta.data["dieta"]["linhas"]
            if linha["ing_form_id"] == self.volumoso_linha.id
        )
        self.assertIsNone(linha_volumoso["preco_kg_mn"])
        self.assertTrue(resposta.data["dieta"]["tem_ingrediente_sem_preco"])
        self.assertEqual(resposta.data["avisos"][0]["codigo"], "PRECO_AUSENTE")

    def test_operadores_e_limites_das_exigencias_sao_preservados(self):
        resposta = self.client.get(self.url)

        requisitos = {
            item["nutriente"]: item
            for item in resposta.data["comparacao_nutricional"]["requisitos"]
        }
        self.assertEqual(requisitos["PB"]["operador"], ">=")
        self.assertEqual(requisitos["PB"]["valor_min"], 14.0)
        self.assertIsNone(requisitos["PB"]["valor_max"])
        self.assertEqual(requisitos["NDT"]["operador"], "ENTRE")
        self.assertEqual(requisitos["NDT"]["valor_min"], 65.0)
        self.assertEqual(requisitos["NDT"]["valor_max"], 75.0)
        self.assertTrue(requisitos["NDT"]["alterado_pelo_usuario"])

    def test_consulta_nao_altera_banco_snapshot_ou_evento(self):
        antes = {
            "formulacao": deepcopy(
                Formulacao.objects.filter(pk=self.formulacao.pk).values().get()
            ),
            "linhas": list(
                IngredienteFormulacao.objects
                .filter(formulacao=self.formulacao)
                .order_by("id")
                .values()
            ),
            "snapshots": SnapshotFormulacao.objects.filter(
                formulacao=self.formulacao
            ).count(),
            "eventos": EventoFormulacao.objects.filter(
                formulacao=self.formulacao
            ).count(),
        }

        resposta = self.client.get(
            self.url,
            {"quantidade_mistura_mn_kg": 300},
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Formulacao.objects.filter(pk=self.formulacao.pk).values().get(),
            antes["formulacao"],
        )
        self.assertEqual(
            list(
                IngredienteFormulacao.objects
                .filter(formulacao=self.formulacao)
                .order_by("id")
                .values()
            ),
            antes["linhas"],
        )
        self.assertEqual(
            SnapshotFormulacao.objects.filter(formulacao=self.formulacao).count(),
            antes["snapshots"],
        )
        self.assertEqual(
            EventoFormulacao.objects.filter(formulacao=self.formulacao).count(),
            antes["eventos"],
        )

    def test_sem_snapshot_retorna_404_explicito(self):
        SnapshotFormulacao.objects.filter(formulacao=self.formulacao).delete()

        resposta = self.client.get(self.url)

        self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("ainda não foram calculados", resposta.data["detail"])

    def test_sem_ingredientes_retorna_erro_explicito(self):
        IngredienteFormulacao.objects.filter(formulacao=self.formulacao).delete()

        resposta = self.client.get(self.url)

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("não possui ingredientes", resposta.data["detail"])
