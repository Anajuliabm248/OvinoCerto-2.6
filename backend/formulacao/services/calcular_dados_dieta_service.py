"""Caso de uso somente leitura para a sessão Dados da Dieta."""

from __future__ import annotations

from formulacao.domain.nutrientes import NUTRIENTES_ORDEM
from formulacao.engines.motor_dados_dieta import EntradaDadosDieta, MotorDadosDieta
from formulacao.models import Formulacao
from formulacao.repositories import IngredienteFormulacaoRepository, SnapshotRepository

# pylint: disable=no-member, too-few-public-methods


class DadosDietaNaoCalculadosError(ValueError):
    """Indica ausência de snapshot compatível com a consulta."""


class CalcularDadosDietaService:
    """Compõe estado persistido e cálculos derivados, sem qualquer escrita."""

    @staticmethod
    def executar(
        formulacao_id: int,
        quantidade_mistura_mn_kg: float | None = None,
    ) -> dict:
        """Retorna os quatro blocos do último snapshot sem modificar estado."""
        formulacao = Formulacao.objects.only(
            "id",
            "custo_mn_kg",
            "custo_ms_kg",
            "custo_animal_dia",
            "custo_lote_dia",
            "quantidade_mistura_mn_kg",
        ).get(pk=formulacao_id)
        quantidade_efetiva_mn_kg = (
            quantidade_mistura_mn_kg
            if quantidade_mistura_mn_kg is not None
            else formulacao.quantidade_mistura_mn_kg
        )
        linhas = IngredienteFormulacaoRepository.get_linhas_dados_dieta(
            formulacao_id
        )
        if not linhas:
            raise ValueError("A formulação não possui ingredientes.")

        snapshot = SnapshotRepository.get_ultimo(formulacao_id)
        if snapshot is None:
            raise DadosDietaNaoCalculadosError(
                "Os dados da dieta ainda não foram calculados."
            )
        payload_snapshot = snapshot.payload or {}
        campos_snapshot = (
            "vetor_total",
            "resultado_adequacao",
            "exigencia_configurada",
        )
        if any(payload_snapshot.get(campo) is None for campo in campos_snapshot):
            raise DadosDietaNaoCalculadosError(
                "O último resultado não contém todos os dados da dieta calculados."
            )

        saida = MotorDadosDieta.calcular(EntradaDadosDieta(
            linhas=linhas,
            quantidade_mistura_mn_kg=quantidade_efetiva_mn_kg,
        ))
        tem_sem_preco = any(
            linha.preco_kg_mn is None
            and linha.participacao_ms_percentual > 1e-12
            for linha in linhas
        )
        dieta_totais = {
            **saida.totais_dieta,
            "custo_mn_kg": formulacao.custo_mn_kg,
            "custo_ms_kg": formulacao.custo_ms_kg,
            "custo_animal_dia": formulacao.custo_animal_dia,
            "custo_lote_dia": formulacao.custo_lote_dia,
            "tem_ingrediente_sem_preco": tem_sem_preco,
        }
        avisos = [
            {
                "codigo": "PRECO_AUSENTE",
                "mensagem": "Ingrediente com participação positiva sem preço informado.",
                "ing_form_id": linha.ing_form_id,
                "nome": linha.nome,
            }
            for linha in linhas
            if linha.preco_kg_mn is None
            and linha.participacao_ms_percentual > 1e-12
        ]

        return {
            "formulacao_id": formulacao.id,
            "versao_num": snapshot.versao_num,
            "quantidade_mistura_mn_kg": quantidade_efetiva_mn_kg,
            "dieta": {
                "linhas": saida.linhas_dieta,
                "totais": dieta_totais,
                "tem_ingrediente_sem_preco": tem_sem_preco,
            },
            "resumo_por_classificacao": saida.resumo_por_classificacao,
            "mistura_concentrada": saida.mistura_concentrada,
            "comparacao_nutricional": _montar_comparacao(
                payload_snapshot,
                saida.mistura_concentrada["ms_percentual_mistura"],
                formulacao,
                snapshot.versao_num,
            ),
            "avisos": avisos,
        }


def _montar_comparacao(
    snapshot: dict,
    ms_percentual_mistura: float | None,
    formulacao: Formulacao,
    versao_num: int,
) -> dict:
    # pylint: disable=too-many-locals
    vetor_total = snapshot.get("vetor_total") or {}
    resultado = snapshot.get("resultado_adequacao") or {}
    desvios = resultado.get("desvios") or []
    desvios_por_nutriente = {
        desvio.get("nutriente"): desvio
        for desvio in desvios
        if desvio.get("nutriente")
    }
    exigencia = snapshot.get("exigencia_configurada") or {}
    configuracoes = exigencia.get("configuracoes") or []
    configuracoes_por_nutriente = {
        config.get("nutriente"): config
        for config in configuracoes
        if config.get("nutriente")
    }

    requisitos = []
    composicao = {}
    for nutriente in NUTRIENTES_ORDEM:
        codigo = nutriente.value
        config = configuracoes_por_nutriente.get(codigo)
        if config is not None:
            requisitos.append({
                "nutriente": codigo,
                "operador": config.get("operador"),
                "valor_min": config.get("valor_min"),
                "valor_max": config.get("valor_max"),
                "valor_origem_nrc": config.get("valor_origem_nrc"),
                "alterado_pelo_usuario": config.get(
                    "alterado_pelo_usuario",
                    False,
                ),
            })
        desvio = desvios_por_nutriente.get(codigo, {})
        composicao[codigo] = {
            "valor": vetor_total.get(codigo),
            "status": desvio.get("status"),
        }

    return {
        "versao_num": versao_num,
        "ms_concentrado_percentual": ms_percentual_mistura,
        "requisitos": requisitos,
        "composicao_dieta": composicao,
        "desvios": desvios,
        "custo_mn_kg": formulacao.custo_mn_kg,
        "custo_animal_dia": formulacao.custo_animal_dia,
    }
