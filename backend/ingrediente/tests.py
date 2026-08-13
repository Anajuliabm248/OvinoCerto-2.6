"""Testes dos contratos de propriedade e preço do catálogo de ingredientes."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Usuario
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

    def test_criacao_rejeita_materia_seca_zero(self):
        """Composição sem matéria seca não entra no catálogo customizado."""
        dados = self._composicao()
        dados['ms'] = 0

        resposta = self.client.post(reverse('ingrediente-list'), dados, format='json')

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ms', resposta.data)
