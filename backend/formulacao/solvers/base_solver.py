"""
Interface abstrata para solvers de formulação.
"""
from abc import ABC, abstractmethod


class BaseSolver(ABC):
    """Interface para solvers de formulação de rações."""

    @abstractmethod
    def solve(self, problema):
        """
        Resolve um problema de formulação.

        Args:
            problema: dict com:
                - ingredientes: list de objetos Ingrediente
                - restricoes: list [{nutriente, operador, valor}, ...]
                - objetivos: list [{tipo, peso}, ...]
                - ingredientes_incluidos: list de IDs
                - ingredientes_excluidos: list de IDs

        Returns:
            dict com:
                - x: dict {ingrediente_id: proporcao}
                - nutrientes: dict {nutriente: valor}
                - custo: float
                - tempo_ms: float
                - status: 'sucesso' | 'inviavel'
                - mensagem: str (se inviável)

        Raises:
            ProblemaInviavelError se não houver solução
        """
        pass

    @abstractmethod
    def pode_resolver(self):
        """
        Verifica se o solver está disponível (dependências instaladas).

        Returns:
            bool
        """
        pass
