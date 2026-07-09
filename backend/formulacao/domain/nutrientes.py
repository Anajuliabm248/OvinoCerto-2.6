"""
Domínio puro - constantes de nutrientes.

Define o conjunto de nutrientes
considerados pelo motor de adequação e a ordem canônica usada
em todos os vetores NumPy (VetorNutricional, ParticipacaoVetor, etc).

Adicionar um novo nutriente = adicionar uma linha em NUTRIENTES_ORDEM.
Todo o resto do domínio (MotorRecalculo, MotorAdequacao, etc) se ajusta
automaticamente, pois itera sobre essa tupla.
"""

# restringe as variáveis a um grupo específico de valores
from enum import Enum


class Nutriente(str, Enum):
    """Nutrientes representados em % da Matéria Seca (MS)."""

    PB = "PB"     # Proteína Bruta
    NDT = "NDT"   # Nutrientes Digestíveis Totais
    FDN = "FDN"   # Fibra em Detergente Neutro
    EE = "EE"     # Extrato Etéreo
    CA = "CA"     # Cálcio
    P = "P"       # Fósforo
    CA_P = "CA_P" # Relação cálcio:fósforo


# Ordem canônica: define o índice de cada nutriente em qualquer array NumPy do domínio.
# CA_P é derivado no total da formulação; em vetores de ingrediente pode vir como 0.
NUTRIENTES_ORDEM: tuple[Nutriente, ...] = (
    Nutriente.PB,
    Nutriente.NDT,
    Nutriente.FDN,
    Nutriente.EE,
    Nutriente.CA,
    Nutriente.P,
    Nutriente.CA_P,
)

N_NUTRIENTES = len(NUTRIENTES_ORDEM)


def indice_de(nutriente: Nutriente) -> int:
    """Retorna a posição de um nutriente no vetor canônico."""
    return NUTRIENTES_ORDEM.index(nutriente)
