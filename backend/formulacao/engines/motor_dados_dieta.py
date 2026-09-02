"""Calculos puros dos quadros da sessao Dados da Dieta."""

from __future__ import annotations

from dataclasses import dataclass
import math


TOLERANCIA_ZERO = 1e-12
CLASSIFICACOES = ("volumoso", "concentrado")

# pylint: disable=too-few-public-methods, too-many-instance-attributes


@dataclass(frozen=True)
class LinhaDadosDietaEntrada:
    """Linha persistida, já alinhada e com preço resolvido pelo repositório."""

    ing_form_id: int
    ingrediente_id: int | None
    classificacao: str
    tipo: str
    nome: str
    ms_percentual_ingrediente: float | None
    ms_kg_dia: float
    mn_kg_dia: float
    participacao_ms_percentual: float
    preco_kg_mn: float | None
    custo_dia: float
    origem_custo: str


@dataclass(frozen=True)
class EntradaDadosDieta:
    """Entradas momentâneas; nenhuma delas é persistida pelo motor."""

    linhas: tuple[LinhaDadosDietaEntrada, ...]
    quantidade_mistura_mn_kg: float | None = None


@dataclass(frozen=True)
class SaidaDadosDieta:
    """Blocos quantitativos que independem de Django, ORM e HTTP."""

    linhas_dieta: tuple[dict, ...]
    totais_dieta: dict
    resumo_por_classificacao: dict
    mistura_concentrada: dict


class MotorDadosDieta:
    """Calcula dieta, resumo e mistura concentrada sem efeitos colaterais."""

    @staticmethod
    def calcular(entrada: EntradaDadosDieta) -> SaidaDadosDieta:
        """Valida entradas e calcula os três blocos quantitativos derivados."""
        if not entrada.linhas:
            raise ValueError("A formulação não possui ingredientes.")
        _validar_quantidade(entrada.quantidade_mistura_mn_kg)
        for linha in entrada.linhas:
            _validar_linha(linha)

        total_ms = sum(linha.ms_kg_dia for linha in entrada.linhas)
        total_mn = sum(linha.mn_kg_dia for linha in entrada.linhas)
        total_participacao_ms = sum(
            linha.participacao_ms_percentual for linha in entrada.linhas
        )
        if total_ms <= TOLERANCIA_ZERO or total_mn <= TOLERANCIA_ZERO:
            raise ValueError("A dieta não possui massas positivas de MS e MN calculadas.")
        if abs(total_participacao_ms - 100.0) > 1e-6:
            raise ValueError(
                "A soma das participações da dieta em MS deve ser 100%; "
                f"recebido {total_participacao_ms}."
            )

        participacoes_mn = _distribuir_exato(
            [linha.mn_kg_dia for linha in entrada.linhas],
            100.0,
        )
        linhas_dieta = tuple(
            {
                "ing_form_id": linha.ing_form_id,
                "ingrediente_id": linha.ingrediente_id,
                "classificacao": linha.classificacao,
                "tipo": linha.tipo,
                "nome": linha.nome,
                "ms_kg_dia": linha.ms_kg_dia,
                "mn_kg_dia": linha.mn_kg_dia,
                "participacao_ms_percentual": linha.participacao_ms_percentual,
                "participacao_mn_percentual": participacoes_mn[pos],
                "preco_kg_mn": linha.preco_kg_mn,
                "custo_dia": linha.custo_dia,
                "origem_custo": linha.origem_custo,
            }
            for pos, linha in enumerate(entrada.linhas)
        )

        totais_dieta = {
            "ms_kg_dia": total_ms,
            "mn_kg_dia": total_mn,
            "participacao_ms_percentual": 100.0,
            "participacao_mn_percentual": sum(participacoes_mn),
        }
        resumo = _calcular_resumo(entrada.linhas, total_ms, total_mn)
        mistura = _calcular_mistura(
            entrada.linhas,
            entrada.quantidade_mistura_mn_kg,
        )
        return SaidaDadosDieta(
            linhas_dieta=linhas_dieta,
            totais_dieta=totais_dieta,
            resumo_por_classificacao=resumo,
            mistura_concentrada=mistura,
        )


def _validar_quantidade(quantidade: float | None) -> None:
    if quantidade is None:
        return
    if not math.isfinite(quantidade) or quantidade <= 0:
        raise ValueError("A quantidade da mistura deve ser finita e maior que zero.")


def _validar_linha(linha: LinhaDadosDietaEntrada) -> None:
    campos = {
        "ms_kg_dia": linha.ms_kg_dia,
        "mn_kg_dia": linha.mn_kg_dia,
        "participacao_ms_percentual": linha.participacao_ms_percentual,
        "custo_dia": linha.custo_dia,
    }
    if linha.preco_kg_mn is not None:
        campos["preco_kg_mn"] = linha.preco_kg_mn
    for nome_campo, valor in campos.items():
        if not math.isfinite(valor) or valor < 0:
            raise ValueError(
                f"Ingrediente {linha.ing_form_id} ({linha.nome}) possui "
                f"{nome_campo} inválido: {valor}."
            )

    if linha.classificacao not in CLASSIFICACOES:
        raise ValueError(
            f"Ingrediente {linha.ing_form_id} ({linha.nome}) possui "
            f"classificação inválida: {linha.classificacao or 'ausente'}."
        )
    if linha.participacao_ms_percentual > TOLERANCIA_ZERO:
        ms = linha.ms_percentual_ingrediente
        if ms is None or not math.isfinite(ms) or ms <= 0 or ms > 100:
            raise ValueError(
                f"Ingrediente {linha.ing_form_id} ({linha.nome}) possui "
                f"MS inválida: {ms}."
            )


def _calcular_resumo(
    linhas: tuple[LinhaDadosDietaEntrada, ...],
    total_ms: float,
    total_mn: float,
) -> dict:
    resumo = {}
    for classificacao in CLASSIFICACOES:
        grupo = tuple(
            linha for linha in linhas if linha.classificacao == classificacao
        )
        ms_grupo = sum(linha.ms_kg_dia for linha in grupo)
        mn_grupo = sum(linha.mn_kg_dia for linha in grupo)
        resumo[classificacao] = {
            "mn_kg_total": mn_grupo,
            "ms_kg_total": ms_grupo,
            "participacao_ms_percentual": sum(
                linha.participacao_ms_percentual for linha in grupo
            ),
            "participacao_mn_percentual": mn_grupo / total_mn * 100.0,
        }
    resumo["total"] = {
        "mn_kg_total": total_mn,
        "ms_kg_total": total_ms,
        "participacao_ms_percentual": 100.0,
        "participacao_mn_percentual": 100.0,
    }
    return resumo


def _calcular_mistura(
    linhas: tuple[LinhaDadosDietaEntrada, ...],
    quantidade: float | None,
) -> dict:
    concentrados = tuple(
        linha for linha in linhas if linha.classificacao == "concentrado"
    )
    total_ms = sum(linha.ms_kg_dia for linha in concentrados)
    total_mn = sum(linha.mn_kg_dia for linha in concentrados)
    disponivel = total_ms > TOLERANCIA_ZERO and total_mn > TOLERANCIA_ZERO

    if not disponivel:
        return {
            "disponivel": False,
            "motivo_indisponibilidade": (
                "SEM_CONCENTRADO_COM_PARTICIPACAO_POSITIVA"
            ),
            "ms_percentual_mistura": None,
            "linhas": [
                _linha_mistura_indisponivel(linha, quantidade)
                for linha in concentrados
            ],
            "totais": {
                "participacao_ms_mistura_percentual": None,
                "mn_kg_por_100kg_mistura": None,
                "mn_kg_para_quantidade": None,
            },
        }

    participacoes_ms = _distribuir_exato(
        [linha.ms_kg_dia for linha in concentrados],
        100.0,
    )
    quantidades_100 = _distribuir_exato(
        [linha.mn_kg_dia for linha in concentrados],
        100.0,
    )
    quantidades_x = (
        None
        if quantidade is None
        else _distribuir_exato(
            [linha.mn_kg_dia for linha in concentrados],
            quantidade,
        )
    )
    linhas_saida = []
    for pos, linha in enumerate(concentrados):
        linhas_saida.append({
            "ing_form_id": linha.ing_form_id,
            "ingrediente_id": linha.ingrediente_id,
            "nome": linha.nome,
            "participacao_ms_mistura_percentual": participacoes_ms[pos],
            "mn_kg_por_100kg_mistura": quantidades_100[pos],
            "mn_kg_para_quantidade": (
                None if quantidades_x is None else quantidades_x[pos]
            ),
        })
    return {
        "disponivel": True,
        "motivo_indisponibilidade": None,
        "ms_percentual_mistura": total_ms / total_mn * 100.0,
        "linhas": linhas_saida,
        "totais": {
            "participacao_ms_mistura_percentual": sum(participacoes_ms),
            "mn_kg_por_100kg_mistura": sum(quantidades_100),
            "mn_kg_para_quantidade": (
                None if quantidades_x is None else sum(quantidades_x)
            ),
        },
    }


def _linha_mistura_indisponivel(
    linha: LinhaDadosDietaEntrada,
    quantidade: float | None,
) -> dict:
    return {
        "ing_form_id": linha.ing_form_id,
        "ingrediente_id": linha.ingrediente_id,
        "nome": linha.nome,
        "participacao_ms_mistura_percentual": 0.0,
        "mn_kg_por_100kg_mistura": 0.0,
        "mn_kg_para_quantidade": 0.0 if quantidade is not None else None,
    }


def _distribuir_exato(pesos: list[float], total: float) -> list[float]:
    soma_pesos = sum(pesos)
    if soma_pesos <= TOLERANCIA_ZERO:
        return [0.0 for _ in pesos]
    valores = [peso / soma_pesos * total for peso in pesos]
    ultimo_positivo = max(pos for pos, peso in enumerate(pesos) if peso > 0)
    valores[ultimo_positivo] += total - sum(valores)
    return valores
