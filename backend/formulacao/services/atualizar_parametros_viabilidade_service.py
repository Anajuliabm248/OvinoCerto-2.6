"""
Application Service - AtualizarParametrosViabilidadeService.

Fase 2 (Custos) — edição do Quadro 10 (Índices Zootécnicos) + Quadro 13
(Valor R$/kg PV) de ParametrosViabilidade.

Puramente ortogonal ao resto do sistema: nunca dispara
RecalcularFormulacaoService nem toca em Lote, ExigenciaConfigurada ou
qualquer participação de ingrediente. O único efeito é sobre o próximo
GET /formulacoes/{id}/viabilidade/ (CalcularViabilidadeService lê os
valores atualizados na hora, sem cache).

Validação de domínio (faixas, positividade) mora aqui — o repositório
(ParametrosViabilidadeRepository.atualizar) só valida que os NOMES de
campo são conhecidos, não os valores.
"""

from __future__ import annotations

from formulacao.models import ParametrosViabilidade
from formulacao.repositories import ParametrosViabilidadeRepository

_VALIDACOES: dict[str, tuple[str, bool]] = {
    # campo: (rótulo para mensagem de erro, permite zero)
    "num_animais":                   ("Número de animais", False),
    "gmd_esperado_kg":               ("GMD esperado (kg)", True),
    "estimativa_permanencia_dias":   ("Estimativa de permanência (dias)", False),
    "peso_entrada_kg":               ("Peso vivo na entrada (kg)", False),
    "cms_percentual_pv":             ("CMS (%) do peso vivo", False),
    "perdas_alimentos_percentual":   ("Perdas de alimentos (%)", True),
    "preco_venda_kg_pv":             ("Preço de venda (R$/kg PV)", False),
}


class AtualizarParametrosViabilidadeService:
    """Atualiza parcialmente um cenário econômico depois de validar cada unidade."""

    @staticmethod
    def executar(formulacao_id: int, **campos) -> ParametrosViabilidade:
        """
        Atualização parcial — só valida e grava os campos informados.

        Levanta ValueError com mensagem específica do campo em caso de
        valor inválido (negativo onde não é permitido, ou zero em
        campo que exige positivo estrito — ex.: estimativa de
        permanência ou CMS%, que entram em denominadores no motor).
        """
        if not campos:
            raise ValueError("Nenhum campo informado para atualização.")

        desconhecidos = set(campos) - set(_VALIDACOES)
        if desconhecidos:
            raise ValueError(f"Campos desconhecidos: {sorted(desconhecidos)}")

        for campo, valor in campos.items():
            AtualizarParametrosViabilidadeService._validar_campo(campo, valor)

        return ParametrosViabilidadeRepository.atualizar(formulacao_id, **campos)

    @staticmethod
    def _validar_campo(campo: str, valor) -> None:
        rotulo, permite_zero = _VALIDACOES[campo]

        if valor is None:
            if campo == "preco_venda_kg_pv":
                return  # único campo opcional — None é "ainda não informado"
            raise ValueError(f"{rotulo} não pode ser vazio.")

        if valor < 0:
            raise ValueError(f"{rotulo} não pode ser negativo.")
        if not permite_zero and valor == 0:
            raise ValueError(f"{rotulo} deve ser maior que zero.")
