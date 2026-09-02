"""Testes dos contratos de propriedade e preço do catálogo de ingredientes."""

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import Usuario
from ingrediente.admin import IngredienteAdmin
from ingrediente.models import (
    HistoricoPrecoIngrediente,
    Ingrediente,
    PrecoIngredienteUsuario,
)


class IngredienteAPITests(APITestCase):
    """Exercita as rotas reais usadas para criar ingredientes e editar preços."""

    def setUp(self):
        """Cria uma conta completa e autentica o cliente de teste."""
        conta = get_user_model().objects.create_user('ana@example.com', password='SenhaForte123!')
        self.conta = conta
        self.perfil = Usuario.objects.create(
            user=conta,
            nome='Ana',
            email='ana@example.com',
            cpf='000.000.000-00',
            telefone='55999999999',
            estado='RS',
            cidade='Santa Maria',
            profissao='Zootecnista',
        )
        self.client.force_authenticate(conta)

    @staticmethod
    def _composicao(nome='Milho'):
        """Monta uma composição mínima válida para os testes HTTP."""
        return {
            'classificacao': 'concentrado',
            'tipo': 'energetico',
            'nome': nome,
            'ms': 88.0,
            'pb': 8.5,
            'ndt': 80.0,
            'fdn': 10.0,
            'ee': 3.5,
            'ca': 0.1,
            'p': 0.3,
            'custo_kg': 1.25,
        }

    def test_criacao_padrao_associa_usuario_e_origem_customizada(self):
        """POST padrão nunca deve criar um ingrediente sem proprietário."""
        resposta = self.client.post(reverse('ingrediente-list'), self._composicao(), format='json')

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        ingrediente = Ingrediente.objects.get(pk=resposta.data['id'])
        self.assertEqual(ingrediente.usuario, self.perfil)
        self.assertFalse(ingrediente.fonte_valadares)

    def test_preco_regional_nao_modifica_catalogo_compartilhado(self):
        """Preço pessoal fica isolado e gera histórico sem alterar custo_kg público."""
        ingrediente = Ingrediente.objects.create(
            **self._composicao('Silagem'),
            fonte_valadares=True,
        )

        resposta = self.client.patch(
            reverse('ingrediente-preco', args=[ingrediente.pk]),
            {'preco': 1.75},
            format='json',
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        ingrediente.refresh_from_db()
        self.assertEqual(ingrediente.custo_kg, 1.25)
        self.assertEqual(
            PrecoIngredienteUsuario.objects.get(
                usuario=self.perfil,
                ingrediente=ingrediente,
            ).preco_kg_mn,
            1.75,
        )
        self.assertTrue(HistoricoPrecoIngrediente.objects.filter(
            usuario=self.perfil,
            ingrediente=ingrediente,
            preco_novo=1.75,
        ).exists())

    def test_patch_padrao_ignora_campos_obrigatorios_vazios(self):
        """A rota usada pela interface mantém valores atuais quando recebe vazio."""
        ingrediente = Ingrediente.objects.create(
            **self._composicao(),
            usuario=self.perfil,
        )

        resposta = self.client.patch(
            reverse('ingrediente-detail', args=[ingrediente.pk]),
            {'nome': '', 'pb': None, 'custo_kg': 1.90},
            format='json',
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        ingrediente.refresh_from_db()
        self.assertEqual(ingrediente.nome, 'Milho')
        self.assertEqual(ingrediente.pb, 8.5)
        self.assertEqual(ingrediente.custo_kg, 1.90)

    def test_listagem_anonima_nao_quebra(self):
        """Requisições públicas devem listar ingredientes sem exigir perfil do usuário."""
        Ingrediente.objects.create(**self._composicao('Milho 2'), fonte_valadares=True)

        cliente = APIClient()
        resposta = cliente.get(reverse('ingrediente-list'), {'valadares': 'true'})

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resposta.data['results']), 1)

    def test_criacao_custom_sem_autenticacao(self):
        """Fluxo simples de teste permite criar ingrediente custom sem login."""
        cliente = APIClient()
        dados = self._composicao('Milho Local')

        resposta = cliente.post(reverse('ingrediente-list'), dados, format='json')

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertFalse(resposta.data['fonte_valadares'])

    def test_listagem_custom_sem_autenticacao_aparece_na_aba_usuario(self):
        """Em modo de teste, ingredientes custom sem usuário devem aparecer na aba de usuário."""
        Ingrediente.objects.create(**self._composicao('Milho Local 2'), fonte_valadares=False, usuario=None)

        cliente = APIClient()
        resposta = cliente.get(reverse('ingrediente-list'), {'valadares': 'false'})

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertTrue(any(item['nome'] == 'Milho Local 2' for item in resposta.data['results']))

    def test_criacao_rejeita_materia_seca_zero(self):
        """Composição sem matéria seca não entra no catálogo customizado."""
        dados = self._composicao()
        dados['ms'] = 0

        resposta = self.client.post(reverse('ingrediente-list'), dados, format='json')

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ms', resposta.data)

    def test_usuario_comum_nao_edita_limites_globais_valadares(self):
        """Usuário comum não pode alterar uma configuração compartilhada."""
        ingrediente = Ingrediente.objects.create(
            **self._composicao('Farelo Valadares'),
            fonte_valadares=True,
        )

        resposta = self.client.patch(
            reverse('ingrediente-detail', args=[ingrediente.pk]),
            {'limite_min_participacao': 2.0, 'limite_max_participacao': 18.0},
            format='json',
        )

        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)
        ingrediente.refresh_from_db()
        self.assertIsNone(ingrediente.limite_min_participacao)
        self.assertIsNone(ingrediente.limite_max_participacao)

    def test_administrador_edita_limites_globais_valadares(self):
        """Administrador pode persistir os limites globais pela rota padrão."""
        self.conta.is_staff = True
        self.conta.save(update_fields=['is_staff'])
        ingrediente = Ingrediente.objects.create(
            **self._composicao('Casca Valadares'),
            fonte_valadares=True,
        )

        resposta = self.client.patch(
            reverse('ingrediente-detail', args=[ingrediente.pk]),
            {'limite_min_participacao': 1.5, 'limite_max_participacao': 22.0},
            format='json',
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        ingrediente.refresh_from_db()
        self.assertEqual(ingrediente.limite_min_participacao, 1.5)
        self.assertEqual(ingrediente.limite_max_participacao, 22.0)

    def test_administrador_nao_edita_composicao_valadares(self):
        """A exceção administrativa não torna os nutrientes públicos editáveis."""
        self.conta.is_staff = True
        self.conta.save(update_fields=['is_staff'])
        ingrediente = Ingrediente.objects.create(
            **self._composicao('Milho Valadares'),
            fonte_valadares=True,
        )

        resposta = self.client.patch(
            reverse('ingrediente-detail', args=[ingrediente.pk]),
            {'pb': 12.0},
            format='json',
        )

        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)
        ingrediente.refresh_from_db()
        self.assertEqual(ingrediente.pb, 8.5)

    def test_admin_libera_somente_limites_em_ingrediente_valadares(self):
        """O formulário administrativo mantém os demais campos somente leitura."""
        ingrediente = Ingrediente.objects.create(
            **self._composicao('Feno Valadares'),
            fonte_valadares=True,
        )
        administracao = IngredienteAdmin(Ingrediente, AdminSite())

        somente_leitura = administracao.get_readonly_fields(None, ingrediente)

        self.assertNotIn('limite_min_participacao', somente_leitura)
        self.assertNotIn('limite_max_participacao', somente_leitura)
        self.assertIn('nome', somente_leitura)
        self.assertIn('pb', somente_leitura)
        self.assertIn('fonte_valadares', somente_leitura)

    def test_modelo_rejeita_limite_minimo_maior_que_maximo(self):
        """O Django Admin recebe a mesma proteção da relação entre limites."""
        ingrediente = Ingrediente(
            **self._composicao('Limites Inválidos'),
            fonte_valadares=True,
            limite_min_participacao=20.0,
            limite_max_participacao=10.0,
        )

        with self.assertRaises(ValidationError) as contexto:
            ingrediente.full_clean()

        self.assertIn('limite_min_participacao', contexto.exception.message_dict)
