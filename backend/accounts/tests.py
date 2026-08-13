"""Testes de autorização dos perfis de usuário."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Perfil, Usuario


class UsuarioAPITests(APITestCase):
    """Garante que um usuário comum só altere dados permitidos do próprio perfil."""

    def test_usuario_nao_pode_promover_o_proprio_perfil(self):
        """O campo perfil é somente leitura, mesmo quando enviado no PATCH."""
        conta = get_user_model().objects.create_user('user@example.com', password='SenhaForte123!')
        perfil = Usuario.objects.create(
            user=conta,
            nome='Usuário',
            email='user@example.com',
            cpf='111.111.111-11',
            telefone='55999999999',
            estado='RS',
            cidade='Santa Maria',
            profissao='Produtor',
        )
        self.client.force_authenticate(conta)

        resposta = self.client.patch(
            reverse('usuario-detail', args=[perfil.pk]),
            {'nome': 'Nome atualizado', 'perfil': Perfil.ADMIN},
            format='json',
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        perfil.refresh_from_db()
        self.assertEqual(perfil.nome, 'Nome atualizado')
        self.assertEqual(perfil.perfil, Perfil.USER)

    def test_alteracao_de_email_atualiza_tambem_o_login(self):
        """Perfil e conta Django não podem ficar com endereços divergentes."""
        conta = get_user_model().objects.create_user('antigo@example.com', password='SenhaForte123!')
        perfil = Usuario.objects.create(
            user=conta,
            nome='Usuário',
            email='antigo@example.com',
            cpf='222.222.222-22',
            telefone='55999999999',
            estado='RS',
            cidade='Santa Maria',
            profissao='Produtor',
        )
        self.client.force_authenticate(conta)

        resposta = self.client.patch(
            reverse('usuario-detail', args=[perfil.pk]),
            {'email': 'NOVO@example.com'},
            format='json',
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        perfil.refresh_from_db()
        conta.refresh_from_db()
        self.assertEqual(perfil.email, 'novo@example.com')
        self.assertEqual(conta.email, 'novo@example.com')
        self.assertEqual(conta.username, 'novo@example.com')
