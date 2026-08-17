"""Regressão da geração inicial com operadores inferidos dos dados publicados.

Esta suíte não usa as participações publicadas como limites do otimizador.
Elas servem exclusivamente para escolher o operador que descreve a relação
observada com o NRC: igual, maior ou igual, ou menor ou igual. A operação
ENTRE não é inferida porque os CSVs não fornecem dois limites independentes.

Para rodar fora desta estação, defina OVINOCERTO_DADOS_REGRESSAO apontando para
a pasta que contém os três CSVs recebidos. Sem ela, os testes são ignorados.
"""

from __future__ import annotations

import csv
import os
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from formulacao.domain.nutrientes import Nutriente, indice_de
from formulacao.domain.participacao import OrigemParticipacao, ParticipacaoVetor
from formulacao.domain.requisito import RequisitoNutriente, StatusAdequacao
from formulacao.engines.estimador_referencia import (
    ContextoZootecnico,
    EstimadorPreferenciaAprendida,
    IngredienteReferencia,
    ReferenciaSuplemento,
)
from formulacao.engines.motor_adequacao import ConfiguracaoIngrediente, MotorAdequacao


TOLERANCIA_ARREDONDAMENTO = 0.01
TOLERANCIA_RECEITA_PP = 0.05

ARQUIVOS = (
    "formulacoes_ovinocerto_testes.csv",
    "exigencias_nutricionais_nrc.csv",
    "ingredientes_composicao_valadares.csv",
)

INGREDIENTES = {
    "trigo_farelo": ("Trigo Farelo", "ENERGETICO", 1.0),
    "milho_grao": ("Milho Grão", "ENERGETICO", 1.0),
    "soja_farelo": ("Soja Farelo", "PROTEICO", 1.0),
    "calcario_calcitico": ("Calcário calcítico", "MINERAL", 1.0),
    "sorgo_grao": ("Sorgo Grão", "ENERGETICO", 1.0),
    "milho_germen_farelo": ("Milho Gérmen Farelo", "ENERGETICO", 1.0),
    "aveia_grao": ("Aveia Grão", "ENERGETICO", 1.0),
    "mandioca_farinha": ("Mandioca Farinha", "ENERGETICO", 1.0),
    "melaco": ("Melaço", "ENERGETICO", 1.0),
    "bicarbonato_sodio": ("Bicarbonato de Sódio", "ADITIVOS", 0.01),
    "cloreto_amonio": ("Cloreto de Amônio", "ADITIVOS", 0.005),
}
NUTRIENTES = (
    (Nutriente.PB, "pb_pct"),
    (Nutriente.NDT, "ndt_pct"),
    (Nutriente.FDN, "fdn_pct"),
    (Nutriente.EE, "ee_pct"),
    (Nutriente.CA, "ca_pct"),
    (Nutriente.P, "p_pct"),
    (Nutriente.CA_P, "ca_p_ratio"),
)
COLUNAS_COMPOSICAO = ("pb_pct", "ndt_pct", "fdn_pct", "ee_pct", "ca_pct", "p_pct")


def _diretorio_dados() -> Path:
    """Localiza a massa externa sem incorporá-la ao código-fonte."""
    candidatos = []
    if caminho_configurado := os.environ.get("OVINOCERTO_DADOS_REGRESSAO"):
        candidatos.append(Path(caminho_configurado))
    candidatos.append(Path(r"C:\Users\anaju\Downloads"))

    for diretorio in candidatos:
        if all((diretorio / arquivo).is_file() for arquivo in ARQUIVOS):
            return diretorio
    pytest.skip(
        "Massa CSV ausente. Defina OVINOCERTO_DADOS_REGRESSAO com a pasta "
        "dos arquivos de regressão."
    )


@pytest.fixture(scope="module")
def massa_csv():
    diretorio = _diretorio_dados()
    with (diretorio / ARQUIVOS[0]).open(encoding="utf-8-sig", newline="") as arquivo:
        formulacoes = list(csv.DictReader(arquivo))
    with (diretorio / ARQUIVOS[1]).open(encoding="utf-8-sig", newline="") as arquivo:
        nrc_por_categoria = {linha["categoria_id"]: linha for linha in csv.DictReader(arquivo)}
    with (diretorio / ARQUIVOS[2]).open(encoding="utf-8-sig", newline="") as arquivo:
        ingredientes = {linha["ingrediente"]: linha for linha in csv.DictReader(arquivo)}
    return formulacoes, nrc_por_categoria, ingredientes


def _requisito_relacional(
    nutriente: Nutriente,
    valor_livro: float,
    valor_nrc: float,
) -> RequisitoNutriente:
    """Escolhe o operador a partir da direção observada, sem usar receita como alvo."""
    # O teste simula o operador explicitamente escolhido para a formulação;
    # por isso ele deve prevalecer sobre o NRC padrão no motor.
    kwargs = {"valor_origem_nrc": valor_nrc, "alterado_pelo_usuario": True}
    if abs(valor_livro - valor_nrc) <= TOLERANCIA_ARREDONDAMENTO:
        return RequisitoNutriente.igual(nutriente, valor_nrc, **kwargs)
    if valor_livro > valor_nrc:
        return RequisitoNutriente.maior_igual(nutriente, valor_nrc, **kwargs)
    return RequisitoNutriente.menor_igual(nutriente, valor_nrc, **kwargs)


def _requisitos_relacionais(linha: dict[str, str], nrc: dict[str, str]):
    return {
        nutriente: _requisito_relacional(
            nutriente,
            float(linha[coluna]),
            float(nrc[coluna]),
        )
        for nutriente, coluna in NUTRIENTES
    }


def _executar_geracao(linha, nrc, composicoes):
    selecionados = [
        codigo
        for codigo in INGREDIENTES
        if float(linha[f"{codigo}_pct_ms"]) > 0.0
    ]
    matriz = np.array([
        [float(composicoes[INGREDIENTES[codigo][0]][coluna]) for coluna in COLUNAS_COMPOSICAO] + [0.0]
        for codigo in selecionados
    ])
    configuracoes = [
        ConfiguracaoIngrediente(
            "CONCENTRADO",
            tipo=INGREDIENTES[codigo][1],
            limite_max=INGREDIENTES[codigo][2],
        )
        for codigo in selecionados
    ]
    participacao = ParticipacaoVetor(
        ids_ingredientes=tuple(range(1, len(selecionados) + 1)),
        fracoes=np.full(len(selecionados), 1.0 / len(selecionados)),
        origens=(OrigemParticipacao.CALCULADA,) * len(selecionados),
    )
    contexto = ContextoZootecnico(
        categoria=f"cordeiros_{linha['fase_meses']}_meses",
        fase="crescimento",
        peso_vivo_kg=float(linha["peso_vivo_kg"]),
        gmd_kg=float(linha["gmd_kg"]),
        cms_kg=float(nrc["cms_kg"]),
    )
    requisitos = _requisitos_relacionais(linha, nrc)
    resultado = MotorAdequacao.redistribuir(
        matriz_M=matriz,
        requisitos=requisitos,
        participacao_atual=participacao,
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.0,
        reiniciar_livres=True,
        contexto_zootecnico=contexto,
    )
    return selecionados, matriz, requisitos, resultado


def _referencias_publicadas(formulacoes, nrc_por_categoria, composicoes):
    """Converte a massa publicada em domínio puro para validação cega."""
    referencias = []
    for linha in formulacoes:
        nrc = nrc_por_categoria[linha["categoria_id"]]
        ingredientes = []
        for codigo, (nome, tipo, _) in INGREDIENTES.items():
            participacao = float(linha[f"{codigo}_pct_ms"]) / 100.0
            if participacao <= 0.0:
                continue
            composicao = composicoes[nome]
            ingredientes.append(IngredienteReferencia(
                classificacao="CONCENTRADO",
                tipo=tipo,
                participacao=participacao,
                composicao=tuple(float(composicao[coluna]) for coluna in COLUNAS_COMPOSICAO),
            ))
        referencias.append(ReferenciaSuplemento(
            contexto=ContextoZootecnico(
                categoria=f"cordeiros_{linha['fase_meses']}_meses",
                fase="crescimento",
                peso_vivo_kg=float(linha["peso_vivo_kg"]),
                gmd_kg=float(linha["gmd_kg"]),
                cms_kg=float(nrc["cms_kg"]),
            ),
            pb=float(nrc["pb_pct"]),
            ndt=float(nrc["ndt_pct"]),
            ca=float(nrc["ca_pct"]),
            p=float(nrc["p_pct"]),
            ca_p=float(nrc["ca_p_ratio"]),
            receita=tuple(item.participacao for item in ingredientes),
            codigo=f"CEGO-{linha['num_formulacao']}",
            ingredientes=tuple(ingredientes),
        ))
    return tuple(referencias)


def test_operadores_explicitos_sao_restricoes_da_geracao():
    """`=`, `>=`, `<=` e `ENTRE` não podem ser apenas penalidades."""
    matriz = np.array([
        [10.0, 70.0, 0.0, 0.0, 2.0, 1.0, 0.0],
        [20.0, 70.0, 0.0, 0.0, 1.0, 1.0, 0.0],
    ])
    configuracoes = [
        ConfiguracaoIngrediente("CONCENTRADO", tipo="ENERGETICO"),
        ConfiguracaoIngrediente("CONCENTRADO", tipo="PROTEICO"),
    ]
    participacao = ParticipacaoVetor(
        ids_ingredientes=(1, 2),
        fracoes=np.array([0.5, 0.5]),
        origens=(OrigemParticipacao.CALCULADA,) * 2,
    )
    requisitos = {
        Nutriente.PB: RequisitoNutriente.igual(
            Nutriente.PB, 15.0, alterado_pelo_usuario=True
        ),
        Nutriente.NDT: RequisitoNutriente.maior_igual(
            Nutriente.NDT, 69.0, alterado_pelo_usuario=True
        ),
        Nutriente.EE: RequisitoNutriente.menor_igual(
            Nutriente.EE, 0.01, alterado_pelo_usuario=True
        ),
        Nutriente.CA_P: RequisitoNutriente.entre(
            Nutriente.CA_P, 1.49, 1.51, alterado_pelo_usuario=True
        ),
    }

    resultado = MotorAdequacao.redistribuir(
        matriz_M=matriz,
        requisitos=requisitos,
        participacao_atual=participacao,
        configuracoes=configuracoes,
        percentual_alvo_volumoso=0.0,
        reiniciar_livres=True,
    )

    totais = resultado.fracoes @ matriz
    totais[indice_de(Nutriente.CA_P)] = (
        totais[indice_de(Nutriente.CA)] / totais[indice_de(Nutriente.P)]
    )
    assert resultado.convergiu
    assert resultado.fracoes.sum() == pytest.approx(1.0)
    for nutriente, requisito in requisitos.items():
        assert requisito.avaliar(totais[indice_de(nutriente)])[0] == StatusAdequacao.ATENDE


def test_classifica_operadores_sem_transformar_receitas_em_regras(massa_csv):
    formulacoes, nrc_por_categoria, _ = massa_csv
    contagem = Counter()

    for linha in formulacoes:
        requisitos = _requisitos_relacionais(linha, nrc_por_categoria[linha["categoria_id"]])
        contagem.update(requisito.operador.value for requisito in requisitos.values())

    assert len(formulacoes) == 116
    assert contagem == Counter({">=": 401, "<=": 278, "=": 133})
    assert "ENTRE" not in contagem


def test_geracao_inicial_com_operadores_relacionais_preserva_invariantes(massa_csv):
    formulacoes, nrc_por_categoria, composicoes = massa_csv

    for linha in formulacoes:
        _, matriz, requisitos, resultado = _executar_geracao(
            linha,
            nrc_por_categoria[linha["categoria_id"]],
            composicoes,
        )
        assert resultado.convergiu, f"Formulação {linha['num_formulacao']} não convergiu"
        assert resultado.fracoes.sum() == pytest.approx(1.0, abs=1e-10)
        totais = resultado.fracoes @ matriz
        totais[indice_de(Nutriente.CA_P)] = (
            totais[indice_de(Nutriente.CA)] / totais[indice_de(Nutriente.P)]
        )
        for nutriente, requisito in requisitos.items():
            status, _ = requisito.avaliar(totais[indice_de(nutriente)])
            assert status == StatusAdequacao.ATENDE, (
                f"Formulação {linha['num_formulacao']} não atende "
                f"{nutriente.value} ({requisito.operador.value})."
            )


def test_preferencia_aprendida_melhora_validacao_cega_das_referencias(massa_csv):
    """O modelo deve superar a heurística sem consultar a fórmula ocultada."""
    formulacoes, nrc_por_categoria, composicoes = massa_csv
    referencias = _referencias_publicadas(
        formulacoes, nrc_por_categoria, composicoes
    )
    erros_aprendidos = []
    erros_heuristicos = []

    for referencia in referencias:
        treino = tuple(item for item in referencias if item.codigo != referencia.codigo)
        matriz = np.array([
            [*ingrediente.composicao, 0.0]
            for ingrediente in referencia.ingredientes
        ])
        configuracoes = [
            ConfiguracaoIngrediente(
                ingrediente.classificacao,
                tipo=ingrediente.tipo,
                limite_max=0.01 if ingrediente.tipo == "ADITIVOS" else 1.0,
            )
            for ingrediente in referencia.ingredientes
        ]
        requisitos = {
            Nutriente.PB: RequisitoNutriente.maior_igual(
                Nutriente.PB, referencia.pb, valor_origem_nrc=referencia.pb
            ),
            Nutriente.NDT: RequisitoNutriente.maior_igual(
                Nutriente.NDT, referencia.ndt, valor_origem_nrc=referencia.ndt
            ),
            Nutriente.CA: RequisitoNutriente.maior_igual(
                Nutriente.CA, referencia.ca, valor_origem_nrc=referencia.ca
            ),
            Nutriente.P: RequisitoNutriente.maior_igual(
                Nutriente.P, referencia.p, valor_origem_nrc=referencia.p
            ),
            Nutriente.CA_P: RequisitoNutriente.maior_igual(
                Nutriente.CA_P, referencia.ca_p, valor_origem_nrc=referencia.ca_p
            ),
        }
        estimativa = EstimadorPreferenciaAprendida.estimar(
            contexto=referencia.contexto,
            requisitos=requisitos,
            matriz_M=matriz,
            classificacoes=tuple(item.classificacao for item in referencia.ingredientes),
            tipos=tuple(item.tipo for item in referencia.ingredientes),
            limites_max=tuple(item.limite_max for item in configuracoes),
            referencias=treino,
            confianca_contextual=0.49,
        )
        assert estimativa is not None
        heuristica = MotorAdequacao._x_alvo_suplemento_concentrado(
            configuracoes, matriz
        )
        esperado = np.array([
            item.participacao for item in referencia.ingredientes
        ])
        mascara_nao_aditivos = np.array([
            item.tipo != "ADITIVOS" for item in referencia.ingredientes
        ])
        erros_aprendidos.extend(
            abs(estimativa.fracoes[mascara_nao_aditivos] - esperado[mascara_nao_aditivos])
        )
        erros_heuristicos.extend(
            abs(heuristica[mascara_nao_aditivos] - esperado[mascara_nao_aditivos])
        )

    assert float(np.mean(erros_aprendidos)) < float(np.mean(erros_heuristicos))


@pytest.mark.xfail(
    reason=(
        "Diagnóstico pendente: a geração inicial ainda não aplica '=' de PB "
        "como restrição efetiva e o objetivo nutricional não determina uma "
        "receita única sem custos e limites adicionais."
    ),
    strict=False,
)
def test_geracao_inicial_com_operadores_relacionais_atende_e_reproduz_referencia(massa_csv):
    """Critério de aceitação futuro; não usa a receita publicada como entrada do motor."""
    formulacoes, nrc_por_categoria, composicoes = massa_csv
    falhas = []

    for linha in formulacoes:
        selecionados, matriz, requisitos, resultado = _executar_geracao(
            linha,
            nrc_por_categoria[linha["categoria_id"]],
            composicoes,
        )
        totais = resultado.fracoes @ matriz
        totais[indice_de(Nutriente.CA_P)] = (
            totais[indice_de(Nutriente.CA)] / totais[indice_de(Nutriente.P)]
        )
        nao_atendidos = [
            nutriente.value
            for nutriente, requisito in requisitos.items()
            if requisito.avaliar(totais[indice_de(nutriente)])[0] != StatusAdequacao.ATENDE
        ]
        percentual_por_ingrediente = dict(zip(selecionados, resultado.fracoes * 100.0))
        maior_erro = max(
            abs(percentual_por_ingrediente.get(codigo, 0.0) - float(linha[f"{codigo}_pct_ms"]))
            for codigo in INGREDIENTES
        )
        if nao_atendidos or maior_erro > TOLERANCIA_RECEITA_PP:
            falhas.append(
                f"f{linha['num_formulacao']}: operadores={nao_atendidos}, "
                f"erro_receita={maior_erro:.2f} pp"
            )

    assert not falhas, "\n".join(falhas)
