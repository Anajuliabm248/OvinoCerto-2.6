"""
Representa a configuração de UM nutriente dentro de uma
ExigenciaConfigurada: o operador escolhido pelo usuário
(=, >=, <=, entre) normalizado para uma representação única
de limites (valor_min, valor_max), ambos em % da MS.

Normalização (ver seção 5.2 do documento de arquitetura):
- "="      -> min == max == valor (com tolerância, ver TOLERANCIA_IGUALDADE)
- ">="     -> min = valor, max = None (sem limite superior)
- "<="     -> min = None, max = valor (sem limite inferior)
- "ENTRE"  -> min = valor_min, max = valor_max (valor_min < valor_max)

Esta normalização é o que permite ao MotorRecalculo e ao
MotorAdequacao tratarem todos os nutrientes de forma uniforme,
sem precisar saber qual operador o usuário escolheu na tela.

"=" nunca é tratado como igualdade estrita: usa-se uma tolerância
mínima (TOLERANCIA_IGUALDADE) para evitar instabilidade numérica
em otimização
"""

# serve para transformar todas as suas dicas de tipagem (type hints) 
# em strings puras durante a leitura do código.
# Isso resolve o problema de referências futuras, permitindo declarar tipos 
# de classes que ainda serão definidos mais abaixo no arquivo.
from __future__ import annotations

from dataclasses import dataclass

# restringe as variáveis a um grupo específico de valores
from enum import Enum

from .nutrientes import Nutriente


class Operador(str, Enum):
    """Operações disponíveis para comparar resultado e exigência nutricional."""
    IGUAL = "="
    MAIOR_IGUAL = ">="
    MENOR_IGUAL = "<="
    ENTRE = "ENTRE"


class StatusAdequacao(str, Enum):
    """Estados possíveis depois da avaliação de um requisito nutricional."""
    ATENDE = "ATENDE"
    DEFICIT = "DEFICIT"
    EXCESSO = "EXCESSO"


@dataclass(frozen=True)
class RequisitoNutriente:
    """
    Configuração normalizada de um nutriente.

    valor_min / valor_max são None quando o operador não impõe
    limite naquele lado (ex.: ">=" não tem valor_max).
    """

    nutriente: Nutriente
    operador: Operador
    valor_min: float | None
    valor_max: float | None

    # Metadados de rastreabilidade (vêm de ConfiguracaoNutriente)
    valor_origem_nrc: float | None = None
    alterado_pelo_usuario: bool = False

    # Tolerância aplicada ao operador "=" para evitar igualdade
    # estrita em otimização (em pontos percentuais de %MS).
    TOLERANCIA_IGUALDADE: float = 0.01

    
    # Validação
    

    def __post_init__(self) -> None:
        if self.operador == Operador.IGUAL:
            if self.valor_min is None or self.valor_max is None:
                raise ValueError("Operador '=' exige valor_min e valor_max definidos")
        elif self.operador == Operador.MAIOR_IGUAL:
            if self.valor_min is None:
                raise ValueError("Operador '>=' exige valor_min definido")
            if self.valor_max is not None:
                raise ValueError("Operador '>=' não deve definir valor_max")
        elif self.operador == Operador.MENOR_IGUAL:
            if self.valor_max is None:
                raise ValueError("Operador '<=' exige valor_max definido")
            if self.valor_min is not None:
                raise ValueError("Operador '<=' não deve definir valor_min")
        elif self.operador == Operador.ENTRE:
            if self.valor_min is None or self.valor_max is None:
                raise ValueError("Operador 'ENTRE' exige valor_min e valor_max definidos")
            if self.valor_min >= self.valor_max:
                raise ValueError(
                    f"Operador 'ENTRE' exige valor_min < valor_max "
                    f"(recebido min={self.valor_min}, max={self.valor_max})"
                )
        else:
            raise ValueError(f"Operador desconhecido: {self.operador}")


    # contrutores
    
    @classmethod
    def igual(
        cls,
        nutriente: Nutriente,
        valor: float,
        *,
        valor_origem_nrc: float | None = None,
        alterado_pelo_usuario: bool = False,
    ) -> "RequisitoNutriente":
        """Cria um alvo com pequena faixa numérica ao redor do valor pedido."""
        tol = cls.TOLERANCIA_IGUALDADE
        return cls(
            nutriente=nutriente,
            operador=Operador.IGUAL,
            valor_min=valor - tol,
            valor_max=valor + tol,
            valor_origem_nrc=valor_origem_nrc,
            alterado_pelo_usuario=alterado_pelo_usuario,
        )

    @classmethod
    def maior_igual(
        cls,
        nutriente: Nutriente,
        valor: float,
        *,
        valor_origem_nrc: float | None = None,
        alterado_pelo_usuario: bool = False,
    ) -> "RequisitoNutriente":
        """Cria um requisito que aceita o valor mínimo sem impor teto."""
        return cls(
            nutriente=nutriente,
            operador=Operador.MAIOR_IGUAL,
            valor_min=valor,
            valor_max=None,
            valor_origem_nrc=valor_origem_nrc,
            alterado_pelo_usuario=alterado_pelo_usuario,
        )

    @classmethod
    def menor_igual(
        cls,
        nutriente: Nutriente,
        valor: float,
        *,
        valor_origem_nrc: float | None = None,
        alterado_pelo_usuario: bool = False,
    ) -> "RequisitoNutriente":
        """Cria um requisito que aceita o valor máximo sem impor piso."""
        return cls(
            nutriente=nutriente,
            operador=Operador.MENOR_IGUAL,
            valor_min=None,
            valor_max=valor,
            valor_origem_nrc=valor_origem_nrc,
            alterado_pelo_usuario=alterado_pelo_usuario,
        )

    @classmethod
    def entre(
        cls,
        nutriente: Nutriente,
        valor_min: float,
        valor_max: float,
        *,
        valor_origem_nrc: float | None = None,
        alterado_pelo_usuario: bool = False,
    ) -> "RequisitoNutriente":
        """Cria uma faixa fechada entre um limite mínimo e outro máximo."""
        return cls(
            nutriente=nutriente,
            operador=Operador.ENTRE,
            valor_min=valor_min,
            valor_max=valor_max,
            valor_origem_nrc=valor_origem_nrc,
            alterado_pelo_usuario=alterado_pelo_usuario,
        )


    # Avaliação

    def avaliar(self, valor_atual: float) -> tuple[StatusAdequacao, float]:
        """
        Compara `valor_atual` (% da MS) contra os limites normalizados.

        Retorna (status, magnitude_relativa):
        - status: ATENDE / DEFICIT / EXCESSO
        - magnitude_relativa: 0.0 se ATENDE; caso contrário, o desvio
          percentual em relação ao limite violado
          (ex.: 0.20 = 20% abaixo/acima do limite).
        """
        if self.valor_min is not None and valor_atual < self.valor_min:
            magnitude = (self.valor_min - valor_atual) / self.valor_min if self.valor_min else 0.0
            return StatusAdequacao.DEFICIT, abs(magnitude)

        if self.valor_max is not None and valor_atual > self.valor_max:
            magnitude = (valor_atual - self.valor_max) / self.valor_max if self.valor_max else 0.0
            return StatusAdequacao.EXCESSO, abs(magnitude)

        return StatusAdequacao.ATENDE, 0.0


    # Apoio para construção de restrições lineares (MotorAdequacao)

    def limites_lp(self) -> tuple[float | None, float | None]:
        """
        Retorna (min, max) prontos para uso em scipy.optimize
        (LinearConstraint), onde None representa ausência de limite
        (equivalente a -inf / +inf).
        """
        return self.valor_min, self.valor_max
