from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Perfil, Usuario


User = get_user_model()


class AccountsAuthTests(TestCase):
    def dados_cadastro(self, **extra):
        dados = {
            'nome': 'Ana Julia',
            'email': 'ana@example.com',
            'cpf': '123.456.789-00',
            'telefone': '(11) 99999-9999',
            'estado': 'SP',
            'cidade': 'Sao Paulo',
            'profissao': 'Produtora',
            'produtor_ovinos': 'on',
            'senha1': 'SenhaForte123',
            'senha2': 'SenhaForte123',
        }
        dados.update(extra)
        return dados

    def criar_usuario(self, email='ana@example.com', perfil=Perfil.USER):
        user = User.objects.create_user(
            username=email,
            email=email,
            password='SenhaForte123',
        )
        Usuario.objects.create(
            user=user,
            nome='Ana Julia',
            email=email,
            cpf='123.456.789-00',
            telefone='(11) 99999-9999',
            estado='SP',
            cidade='Sao Paulo',
            profissao='Produtora',
            perfil=perfil,
        )
        return user

    def test_cadastro_cria_usuario_e_perfil(self):
        response = self.client.post(reverse('accounts:cadastro'), self.dados_cadastro())

        self.assertRedirects(response, reverse('accounts:index'))
        user = User.objects.get(email='ana@example.com')
        self.assertEqual(user.perfil_usuario.perfil, Perfil.USER)
        self.assertTrue(user.perfil_usuario.produtor_ovinos)

    def test_login_por_email(self):
        self.criar_usuario()

        response = self.client.post(
            reverse('accounts:login'),
            {'email': 'ana@example.com', 'senha': 'SenhaForte123'},
        )

        self.assertRedirects(response, reverse('accounts:index'))

    def test_usuario_comum_nao_acessa_gerenciamento(self):
        user = self.criar_usuario()
        self.client.force_login(user)

        response = self.client.get(reverse('accounts:usuarios'))

        self.assertRedirects(response, reverse('accounts:index'))

    def test_admin_do_sistema_acessa_gerenciamento(self):
        user = self.criar_usuario(email='admin@example.com', perfil=Perfil.ADMIN)
        self.client.force_login(user)

        response = self.client.get(reverse('accounts:usuarios'))

        self.assertEqual(response.status_code, 200)

    def test_superusuario_sem_perfil_acessa_gerenciamento(self):
        user = User.objects.create_superuser(
            username='root@example.com',
            email='root@example.com',
            password='SenhaForte123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('accounts:usuarios'))

        self.assertEqual(response.status_code, 200)
