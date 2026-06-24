"""
Agregado final produzido pelo MotorRecalculo:
reúne o DesvioNutricional de cada nutriente configurado + o estado
da soma das participações (%MS).

É este objeto que:
- alimenta o MotorAlertas;
- alimenta o MotorSugestao via `vetor_necessidade()`;
- é serializado dentro do `payload_json` de SnapshotFormulacao, 
  com `SCHEMA_VERSION` para permitir evolução do formato sem quebrar snapshots antigos.
"""

from __future__ import annotations

from dataclasses import dataclass

from .desvio import DesvioNutricional
from .nutrientes import Nutriente
from .participacao import TOLERANCIA_SOMA
from .requisito import StatusAdequacao
from .vetor_nutricional import VetorNutricional
from .requisito import RequisitoNutriente


@dataclass(frozen=True)
class ResultadoAdequacao:
    """
    desvios             : um DesvioNutricional por nutriente configurado,
                          na ordem em que foram avaliados.
    soma_participacoes  : Σ fracoes (0-1) no momento do cálculo.
    soma_valida         : True se soma_participacoes ≈ 1.0 (tolerância
                          TOLERANCIA_SOMA, equivalente a [99.9%, 100.1%]).
    """

    desvios: tuple[DesvioNutricional, ...]
    soma_participacoes: float
    soma_valida: bool

    # Versão do formato do payload serializado
    SCHEMA_VERSION: int = 1


    # Construtor

    @classmethod
    def calcular(
        cls,
        vetor_total: VetorNutricional,
        requisitos: dict[Nutriente, RequisitoNutriente],
        soma_participacoes: float,
        tolerancia_soma: float = TOLERANCIA_SOMA,
    ) -> "ResultadoAdequacao":
        """
        vetor_total : valores nutricionais totais da formulação
                      (já agregados, em % da MS).
        requisitos  : dict {Nutriente: RequisitoNutriente}, vindo da
                      ExigenciaConfigurada.
        """
        desvios = tuple(
            DesvioNutricional.calcular(
                nutriente=nutriente,
                valor_atual=vetor_total.get(nutriente),
                requisito=requisito,
            )
            for nutriente, requisito in requisitos.items()
        )
        return cls(
            desvios=desvios,
            soma_participacoes=soma_participacoes,
            soma_valida=abs(soma_participacoes - 1.0) <= tolerancia_soma,
        )


    # Consultas

    @property
    def atende_tudo(self) -> bool:
        return all(d.atende for d in self.desvios)

    def desvio_de(self, nutriente: Nutriente) -> DesvioNutricional | None:
        for d in self.desvios:
            if d.nutriente == nutriente:
                return d
        return None

    def em_deficit(self) -> tuple[DesvioNutricional, ...]:
        return tuple(d for d in self.desvios if d.status == StatusAdequacao.DEFICIT)

    def em_excesso(self) -> tuple[DesvioNutricional, ...]:
        return tuple(d for d in self.desvios if d.status == StatusAdequacao.EXCESSO)

    def vetor_necessidade(self) -> dict[Nutriente, float]:
        """
        Vetor de necessidade usado pelo MotorSugestao (seção 10):
        {nutriente: sinal_necessidade}, onde positivo = déficit,
        negativo = excesso, 0 = atende.
        """
        return {d.nutriente: d.sinal_necessidade for d in self.desvios}


    # Severidade da soma de participações (apoio ao MotorAlertas)

    def desvio_soma_pontos_percentuais(self) -> float:
        """Quanto a soma de participações está distante de 100%, em pontos percentuais."""
        return abs(self.soma_participacoes - 1.0) * 100.0


    # Serialização (payload jsonb do SnapshotFormulacao)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "soma_participacoes": self.soma_participacoes,
            "soma_valida": self.soma_valida,
            "atende_tudo": self.atende_tudo,
            "desvios": [d.to_dict() for d in self.desvios],
        }