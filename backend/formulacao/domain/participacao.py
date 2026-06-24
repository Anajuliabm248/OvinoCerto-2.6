"""
Representa o conjunto de participações (%MS, em fração 0-1) de
todos os ingredientes de uma formulação, junto com a marcação de
quais estão "travados" pelo usuário (origem_participacao =
MANUAL_TRAVADA) e quais são "livres" para recálculo/redistribuição
automática (CALCULADA).

as fracoes aqui são SEMPRE valores 0-1 (ex.: 0.30
para 30%), nunca 0-100. Um bug de escala nesse ponto faz todas as
restrições nutricionais errarem por um fator de 100.

Este VO não conhece banco de dados, IDs de tabela específicos nem
Django - `ids_ingredientes` é apenas uma referência opaca (int)
usada pelos repositórios para remontar o resultado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class OrigemParticipacao(str, Enum):
    """
    CALCULADA      -> participação definida/ajustada pelo sistema
                      (geração inicial ou redistribuição automática).
    MANUAL_TRAVADA -> usuário editou manualmente esta participação;
                      nunca é alterada automaticamente por redistribuição
    """

    CALCULADA = "CALCULADA"
    MANUAL_TRAVADA = "MANUAL_TRAVADA"


# Tolerância padrão para considerar Σ fracoes ≈ 1.0 (soma 100%).
# Equivalente a [99.9%, 100.1%]
TOLERANCIA_SOMA = 0.001


@dataclass(frozen=True)
class ParticipacaoVetor:
    """
    ids_ingredientes : tupla de identificadores opacos (ex.: id de
                        IngredienteFormulacao), na mesma ordem das
                        demais listas/arrays.
    fracoes          : np.ndarray 1D, shape (n,), valores em [0, 1].
    origens          : tupla de OrigemParticipacao, shape (n,).
    """

    ids_ingredientes: tuple[int, ...]
    fracoes: np.ndarray = field(repr=False)
    origens: tuple[OrigemParticipacao, ...]


    # Validação

    def __post_init__(self) -> None:
        n = len(self.ids_ingredientes)

        if self.fracoes.shape != (n,):
            raise ValueError(
                f"ParticipacaoVetor: fracoes tem shape {self.fracoes.shape}, "
                f"esperado ({n},)"
            )
        if len(self.origens) != n:
            raise ValueError(
                f"ParticipacaoVetor: origens tem {len(self.origens)} itens, "
                f"esperado {n}"
            )
        if n == 0:
            # Formulação vazia é inválida,
            # mas a validação de "não permitir" é responsabilidade do
            # Application Service - aqui apenas permitimos o estado
            # vazio existir como VO (ex.: antes de selecionar ingredientes).
            return
        
        # valida se a fração está entre -0.0000000001 ou 1.0000000001
        if np.any(self.fracoes < -1e-9) or np.any(self.fracoes > 1 + 1e-9):
            raise ValueError(
                "ParticipacaoVetor: todas as fracoes devem estar em [0, 1] "
                "(valores em 0-100 indicam bug de escala - ver seção 2)"
            )


    # Construtores

    @classmethod
    def from_items(cls, itens: list[dict]) -> "ParticipacaoVetor":
        """
        Constrói a partir de uma lista de dicts:
          [{"id": 1, "fracao": 0.30, "origem": "CALCULADA"}, ...]

        `fracao` deve estar em 0-1 (não em percentual 0-100).
        """
        ids = tuple(int(item["id"]) for item in itens)
        fracoes = np.array([float(item["fracao"]) for item in itens], dtype=float)
        origens = tuple(OrigemParticipacao(item["origem"]) for item in itens)
        return cls(ids_ingredientes=ids, fracoes=fracoes, origens=origens)


    # Consultas

    def __len__(self) -> int:
        return len(self.ids_ingredientes)

    def soma(self) -> float:
        return float(np.sum(self.fracoes)) if len(self) else 0.0

    def soma_valida(self, tolerancia: float = TOLERANCIA_SOMA) -> bool:
        return abs(self.soma() - 1.0) <= tolerancia

    def mascara_travados(self) -> np.ndarray:
        """Array booleano: True onde origem == MANUAL_TRAVADA."""
        return np.array(
            [o == OrigemParticipacao.MANUAL_TRAVADA for o in self.origens],
            dtype=bool,
        )

    def mascara_livres(self) -> np.ndarray:
        return ~self.mascara_travados()

    def soma_travados(self) -> float:
        mascara = self.mascara_travados()
        return float(np.sum(self.fracoes[mascara])) if len(self) else 0.0

    def soma_livres(self) -> float:
        mascara = self.mascara_livres()
        return float(np.sum(self.fracoes[mascara])) if len(self) else 0.0

    def espaco_livre(self) -> float:
        """
        Espaço percentual (0-1) disponível para os ingredientes livres,
        de forma que a soma total continue em 1.0.

        Usado pelo MotorAdequacao.redistribuir(). Se
        espaco_livre <= 0, há mais participação travada do que 100%
        e a redistribuição automática não deve ocorrer (gerar alerta).
        """
        return 1.0 - self.soma_travados()


    # Transformações (sempre retornam nova instância - imutável)

    def com_fracoes(self, novas_fracoes: np.ndarray) -> "ParticipacaoVetor":
        """Retorna uma nova ParticipacaoVetor com as fracoes substituídas."""
        return ParticipacaoVetor(
            ids_ingredientes=self.ids_ingredientes,
            fracoes=novas_fracoes,
            origens=self.origens,
        )

    def com_origem(self, id_ingrediente: int, nova_origem: OrigemParticipacao) -> "ParticipacaoVetor":
        """
        Retorna uma nova ParticipacaoVetor com a origem de um ingrediente
        específico alterada (ex.: usuário edita manualmente -> MANUAL_TRAVADA).
        """
        novas_origens = tuple(
            nova_origem if id_ == id_ingrediente else origem
            for id_, origem in zip(self.ids_ingredientes, self.origens)
        )
        return ParticipacaoVetor(
            ids_ingredientes=self.ids_ingredientes,
            fracoes=self.fracoes,
            origens=novas_origens,
        )


    # Serialização

    def to_dicts(self) -> list[dict]:
        return [
            {"id": id_, "fracao": float(fracao), "origem": origem.value}
            for id_, fracao, origem in zip(self.ids_ingredientes, self.fracoes, self.origens)
        ]