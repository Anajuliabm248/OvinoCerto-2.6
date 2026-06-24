"""
Representação canônica (NumPy) dos valores nutricionais de UM
ingrediente ou de UMA formulação inteira, sempre em % da Matéria
Seca (MS) e sempre na ordem definida por NUTRIENTES_ORDEM.

Por que isso existe (ver seção 2.2 do documento de arquitetura):
EXIGENCIA_NRC e INGREDIENTE misturam unidades absolutas (_kg, _g) e
relativas (%). Para que comparadores configuráveis (=, >=, <=, entre)
funcionem de forma consistente, todo o motor opera sobre esta
representação única: % da MS.

Conversões para massa absoluta (kg/dia) ficam fora deste VO -
são responsabilidade do MotorRecalculo, que multiplica por CMS_total.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .nutrientes import N_NUTRIENTES, NUTRIENTES_ORDEM, Nutriente


@dataclass(frozen=True)
class VetorNutricional:
    """
    Vetor imutável de valores nutricionais em % da MS.

    `valores` é um np.ndarray 1D de shape (vetor) (N_NUTRIENTES,),
    na ordem de NUTRIENTES_ORDEM.
    """

    valores: np.ndarray = field(repr=False)

    def __post_init__(self) -> None:
        if self.valores.shape != (N_NUTRIENTES,):
            raise ValueError(
                f"VetorNutricional espera shape ({N_NUTRIENTES},), "
                f"recebido {self.valores.shape}"
            )


    # Construtores

    @classmethod
    def zeros(cls) -> "VetorNutricional":
        return cls(valores=np.zeros(N_NUTRIENTES, dtype=float))

    @classmethod
    def from_dict(cls, dados: dict[str, float]) -> "VetorNutricional":
        """
        Cria a partir de um dict {"PB": 18.5, "NDT": 70.0, ...}.
        Nutrientes ausentes no dict assumem 0.0.
        """
        valores = np.array(
            [float(dados.get(n.value, 0.0)) for n in NUTRIENTES_ORDEM],
            dtype=float,
        )
        return cls(valores=valores)


    # Acesso

    def get(self, nutriente: Nutriente) -> float:
        idx = NUTRIENTES_ORDEM.index(nutriente)
        return float(self.valores[idx])

    def to_dict(self) -> dict[str, float]:
        return {n.value: float(self.valores[i]) for i, n in enumerate(NUTRIENTES_ORDEM)}


    # Operações vetoriais

    def __add__(self, outro: "VetorNutricional") -> "VetorNutricional":
        return VetorNutricional(valores=self.valores + outro.valores)

    def __mul__(self, escalar: float) -> "VetorNutricional":
        """Escala o vetor por um escalar (ex.: fração de %MS de um ingrediente)."""
        return VetorNutricional(valores=self.valores * float(escalar))

    __rmul__ = __mul__

    def __repr__(self) -> str:
        partes = ", ".join(
            f"{n.value}={v:.3f}" for n, v in zip(NUTRIENTES_ORDEM, self.valores)
        )
        return f"VetorNutricional({partes})"