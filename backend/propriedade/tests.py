from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Perfil, Usuario

from .models import Propriedade


User = get_user_model()


class PropriedadeViewsTests(TestCase):
    def criar_usuario(self, email='ana@example.com', cpf='123.456.789-00'):
        user = User.objects.create_user(
            username=email,
            email=email,
            password='SenhaForte123',
        )
        perfil = Usuario.objects.create(
            user=user,
            nome='Ana Julia',
            email=email,
            cpf=cpf,
            telefone='(11) 99999-9999',
            estado='RS',
            cidade='Santa Maria',
            profissao='Produtora',
            perfil=Perfil.USER,
        )
        return user, perfil

    def criar_propriedade(self, perfil, nome='Fazenda Nova'):
        return Propriedade.objects.create(
            usuario=perfil,
            nome=nome,
            cnpj=f'12.345.678/{perfil.id:04d}-90',
            proprietario=perfil.nome,
            telefone=perfil.telefone,
            uf='RS',
            cidade='Santa Maria',
            localidade='Interior',
        )

    def test_listar_filtra_por_perfil_do_usuario_logado(self):
        user, perfil = self.criar_usuario()
        _, outro_perfil = self.criar_usuario(
            email='outra@example.com',
            cpf='987.654.321-00',
        )
        self.criar_propriedade(perfil, nome='Fazenda da Ana')
        self.criar_propriedade(outro_perfil, nome='Fazenda de Outra Pessoa')
        self.client.force_login(user)

        response = self.client.get(reverse('propriedade:listar'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fazenda da Ana')
        self.assertNotContains(response, 'Fazenda de Outra Pessoa')

    def test_cadastrar_salva_propriedade_com_perfil_do_usuario_logado(self):
        user, perfil = self.criar_usuario()
        self.client.force_login(user)

        response = self.client.post(reverse('propriedade:cadastrar'), {
            'nome': 'Fazenda Cordeiro',
            'cnpj': '12.345.678/0001-90',
            'proprietario': 'Ana Julia',
            'telefone': '(55) 99999-9999',
            'uf': 'rs',
            'cidade': 'Santa Maria',
            'localidade': 'Interior',
        })

        self.assertRedirects(response, reverse('propriedade:listar'))
        propriedade = Propriedade.objects.get(nome='Fazenda Cordeiro')
        self.assertEqual(propriedade.usuario, perfil)
        self.assertEqual(propriedade.uf, 'RS')
