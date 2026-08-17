import numpy as np
import pytest

from formulacao.services.gerar_formulacao_inicial_service import (
    GerarFormulacaoInicialService,
)


def test_menor_custo_rejeita_ingrediente_sem_preco():
    with pytest.raises(ValueError, match="Sorgo"):
        GerarFormulacaoInicialService._validar_precos_para_objetivo(
            objetivo="MENOR_CUSTO",
            nomes_ingredientes=["Milho", "Sorgo"],
            custos_kg_mn=np.array([1.20, 0.0]),
        )


def test_equilibrado_nao_exige_preco():
    GerarFormulacaoInicialService._validar_precos_para_objetivo(
        objetivo="EQUILIBRADO",
        nomes_ingredientes=["Milho", "Sorgo"],
        custos_kg_mn=np.array([1.20, 0.0]),
    )


def test_menor_custo_aceita_quando_todos_os_precos_sao_validos():
    GerarFormulacaoInicialService._validar_precos_para_objetivo(
        objetivo="MENOR_CUSTO",
        nomes_ingredientes=["Milho", "Sorgo"],
        custos_kg_mn=np.array([1.20, 0.95]),
    )
