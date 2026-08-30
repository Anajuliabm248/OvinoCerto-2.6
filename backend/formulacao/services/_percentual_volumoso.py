"""Regras centrais do estado e do resultado do percentual de volumoso."""

from __future__ import annotations

from formulacao.models import (
    Formulacao,
    ModoPercentualVolumoso,
    OrigemPercentualVolumoso,
)


def resolver_configuracao_volumoso(
    formulacao: Formulacao,
    modo_solicitado: str | None,
    percentual_solicitado: float | None,
) -> tuple[str, float | None, str]:
    """Retorna (modo, alvo_para_motor, origem) sem fontes concorrentes."""
    modo = modo_solicitado
    if modo is None:
        modo = (
            ModoPercentualVolumoso.FIXADO_PELO_USUARIO
            if percentual_solicitado is not None
            else formulacao.modo_percentual_volumoso
        )
    if modo not in ModoPercentualVolumoso.values:
        opcoes = ", ".join(ModoPercentualVolumoso.values)
        raise ValueError(f"Modo de percentual de volumoso invalido. Use: {opcoes}.")

    if modo == ModoPercentualVolumoso.OTIMIZADO_PELO_SISTEMA:
        if percentual_solicitado is not None:
            raise ValueError(
                "Nao informe percentual no modo OTIMIZADO_PELO_SISTEMA."
            )
        return modo, None, OrigemPercentualVolumoso.SISTEMA

    percentual = (
        percentual_solicitado
        if percentual_solicitado is not None
        else formulacao.percentual_alvo_volumoso
    )
    if percentual is None:
        raise ValueError(
            "Informe o percentual de volumoso ao usar FIXADO_PELO_USUARIO."
        )
    percentual = float(percentual)
    if not 0.0 <= percentual <= 1.0:
        raise ValueError("O percentual de volumoso deve estar entre 0% e 100%.")
    return modo, percentual, OrigemPercentualVolumoso.USUARIO


def percentual_volumoso_aplicado(fracoes, configuracoes) -> float:
    """Soma as fracoes classificadas como volumoso no resultado do motor."""
    return float(sum(
        float(fracao)
        for fracao, configuracao in zip(fracoes, configuracoes, strict=True)
        if configuracao.classificacao == "VOLUMOSO"
    ))


def obter_alvo_volumoso_para_motor(formulacao_id: int) -> float | None:
    """Carrega o estado controlador e nunca usa o aplicado como configuracao."""
    formulacao = Formulacao.objects.only(
        "modo_percentual_volumoso",
        "percentual_alvo_volumoso",
    ).get(pk=formulacao_id)
    return formulacao.percentual_volumoso_para_motor
