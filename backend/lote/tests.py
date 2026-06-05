from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Perfil, Usuario
from propriedade.models import Propriedade

from .models import Lote


User = get_user_model()


class LoteViewsTests(TestCase):
    def criar_usuario_com_propriedade(self):
        user = User.objects.create_user(
            username='ana@example.com',
            email='ana@example.com',
            password='SenhaForte123',
        )
        perfil = Usuario.objects.create(
            user=user,
            nome='Ana Julia',
            email='ana@example.com',
            cpf='123.456.789-00',
            telefone='(11) 99999-9999',
            estado='RS',
            cidade='Santa Maria',
            profissao='Produtora',
            perfil=Perfil.USER,
        )
        propriedade = Propriedade.objects.create(
            usuario=perfil,
            nome='Fazenda da Ana',
            cnpj='12.345.678/0001-90',
            proprietario=perfil.nome,
            telefone=perfil.telefone,
            uf='RS',
            cidade='Santa Maria',
            localidade='Interior',
        )
        return user, propriedade

    def test_listar_lotes_usa_perfil_do_usuario_logado(self):
        user, propriedade = self.criar_usuario_com_propriedade()
        Lote.objects.create(
            propriedade=propriedade,
            nome_lote='Lote Matrizes',
            raca='Dorper',
            sistema='Confinamento',
            categoria='ovelhas',
            fase='manutencao',
            peso_vivo=60,
            gmd_esperado=0.2,
            num_animais=30,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('lote:listar', kwargs={
            'propriedade_id': propriedade.id,
        }))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lote Matrizes')
