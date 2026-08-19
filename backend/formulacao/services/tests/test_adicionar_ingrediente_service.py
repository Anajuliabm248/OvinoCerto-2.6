from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Usuario
from formulacao.models import EventoFormulacao, Formulacao, IngredienteFormulacao
from formulacao.services.adicionar_ingrediente_service import AdicionarIngredienteService
from ingrediente.models import Ingrediente
from lote.models import Lote
from propriedade.models import Propriedade


class AdicionarIngredienteServiceTests(TestCase):
    def setUp(self):
        conta = get_user_model().objects.create_user(
            username="rascunho-ingredientes",
            password="senha-de-teste",
        )
        usuario = Usuario.objects.create(
            user=conta,
            nome="Usuário de teste",
            email="rascunho@example.com",
            cpf="12345678900",
            telefone="55999999999",
            estado="RS",
            cidade="Santa Maria",
            profissao="Produtor",
        )
        propriedade = Propriedade.objects.create(
            usuario=usuario,
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
            usuario=usuario,
            titulo="Formulação em montagem",
        )
        self.ingrediente = Ingrediente.objects.create(
            classificacao="concentrado",
            tipo="energetico",
            nome="Milho",
            ms=88.0,
            pb=9.0,
            ndt=80.0,
            fdn=12.0,
            ee=4.0,
            ca=0.1,
            p=0.3,
            custo_kg=1.0,
            fonte_valadares=True,
        )

    def test_adiciona_ingrediente_sem_exigir_volumoso_antes_da_geracao_inicial(self):
        linha = AdicionarIngredienteService.executar(
            formulacao_id=self.formulacao.id,
            ingrediente_id=self.ingrediente.id,
        )

        self.assertEqual(linha.ms_porcent, 0.0)
        self.assertTrue(
            IngredienteFormulacao.objects.filter(
                formulacao=self.formulacao,
                ingrediente=self.ingrediente,
            ).exists()
        )
        evento = EventoFormulacao.objects.get(formulacao=self.formulacao)
        self.assertTrue(evento.payload["geracao_inicial_pendente"])
