from django.test import TestCase

from formulacao.services.atualizar_preco_ingrediente_service import _atualizar_preco_catalogo
from ingrediente.models import Ingrediente


class AtualizarPrecoIngredienteServiceTests(TestCase):
    def test_atualizar_preco_catalogo_salva_custo_sem_campo_inexistente(self):
        ingrediente = Ingrediente.objects.create(
            classificacao='concentrado',
            tipo='energetico',
            nome='Milho',
            ms=88.0,
            pb=8.5,
            ndt=80.0,
            fdn=10.0,
            ee=3.5,
            ca=0.1,
            p=0.3,
            custo_kg=1.25,
        )

        _atualizar_preco_catalogo(ingrediente, 1.75)

        ingrediente.refresh_from_db()
        self.assertEqual(ingrediente.custo_kg, 1.75)
