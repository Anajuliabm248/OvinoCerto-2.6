"""
Resultado da comparação entre o valor calculado de um nutriente
(para a formulação inteira, em % da MS) e o RequisitoNutriente
configurado para ele.

É a unidade básica que compõe o ResultadoAdequacao (seção 7,
passo 5/6 do documento de arquitetura) e a entrada principal do
MotorAlertas (seção 12) e do MotorSugestao (seção 10).
"""

from __future__ import annotations

from dataclasses import dataclass

from .nutrientes import Nutriente
from .requisito import RequisitoNutriente, StatusAdequacao


@dataclass(frozen=True)
class DesvioNutricional:
    """
    Desvio de um nutriente específico em relação ao requisito configurado.

    - status: ATENDE / DEFICIT / EXCESSO (vem de RequisitoNutriente.avaliar)
    - magnitude_relativa: 0.0 se ATENDE; senão, o quanto o valor está
      fora do limite, em proporção do próprio limite (ex.: 0.20 = 20%).
    """

    nutriente: Nutriente
    valor_atual: float
    requisito: RequisitoNutriente
    status: StatusAdequacao
    magnitude_relativa: float

    
    # Construtor
    

    @classmethod
    def calcular(
        cls,
        nutriente: Nutriente,
        valor_atual: float,
        requisito: RequisitoNutriente,
    ) -> "DesvioNutricional":
        status, magnitude = requisito.avaliar(valor_atual)
        return cls(
            nutriente=nutriente,
            valor_atual=valor_atual,
            requisito=requisito,
            status=status,
            magnitude_relativa=magnitude,
        )

    
    # Propriedades de apoio
    

    @property
    def atende(self) -> bool:
        return self.status == StatusAdequacao.ATENDE

    @property
    def sinal_necessidade(self) -> float:
        """
        Vetor de necessidade usado pelo MotorSugestao (seção 10):

        - DEFICIT  -> valor positivo (queremos MAIS deste nutriente)
        - EXCESSO  -> valor negativo (queremos MENOS deste nutriente)
        - ATENDE   -> 0.0 (neutro)

        A magnitude reflete o quão longe está do limite, permitindo
        priorizar os déficits/excessos mais graves no ranking de
        ingredientes candidatos.
        """
        if self.status == StatusAdequacao.DEFICIT:
            return self.magnitude_relativa
        if self.status == StatusAdequacao.EXCESSO:
            return -self.magnitude_relativa
        return 0.0

    
    # Serialização (para snapshots / payload jsonb)
    

    def to_dict(self) -> dict:
        return {
            "nutriente": self.nutriente.value,
            "valor_atual": self.valor_atual,
            "operador": self.requisito.operador.value,
            "valor_min": self.requisito.valor_min,
            "valor_max": self.requisito.valor_max,
            "alterado_pelo_usuario": self.requisito.alterado_pelo_usuario,
            "status": self.status.value,
            "magnitude_relativa": self.magnitude_relativa,
        }