"""
Validador de soluções do solver.
"""
from ..utils.constants import (
    TOLERANCIA_SOMA,
    TOLERANCIA_IGUALDADE_NUTRIENTE,
    TOLERANCIA_PERCENTUAL,
)
from ..utils.nutrient_calculator import (
    calcular_nutrientes_totais,
    validar_soma_proporcoes,
    validar_atendimento_restricao,
)


class SolucaoInvalidaError(Exception):
    """Levantada quando a solução não é válida."""
    pass


class SolutionValidator:
    """Valida soluções retornadas pelo solver."""

    def validar_solucao(self, solucao, problema):
        """
        Valida uma solução completa.

        Args:
            solucao: dict com x (proporções), nutrientes, custo, etc.
            problema: dict com ingredientes, restrições, etc.

        Returns:
            dict validado com detalhes

        Raises:
            SolucaoInvalidaError se há problemas críticos
        """
        erros = []
        avisos = []

        # 1. Validar soma de proporções
        try:
            is_valid, soma = validar_soma_proporcoes(
                solucao['x'],
                TOLERANCIA_SOMA
            )
            if not is_valid:
                erros.append(f"Soma de proporções = {soma}%, esperado 100%")
        except Exception as e:
            erros.append(f"Erro ao validar soma: {str(e)}")

        # 2. Validar que nenhuma proporção é negativa
        for ing_id, prop in solucao['x'].items():
            if prop < -1e-6:  # Pequena tolerância para erros numéricos
                erros.append(f"Ingrediente {ing_id} tem proporção negativa: {prop}%")
            elif prop > 100 + 1e-6:
                erros.append(f"Ingrediente {ing_id} tem proporção > 100%: {prop}%")
            elif prop < 0.01 and prop > 0:
                avisos.append(f"Ingrediente {ing_id} tem proporção muito pequena: {prop}%")

        # 3. Validar restrições nutricionais
        restricoes_violadas = []
        for restricao in problema.get('restricoes', []):
            nutriente = restricao['nutriente']
            valor_exigido = restricao['valor']
            operador = restricao['operador']

            valor_obtido = solucao.get('nutrientes', {}).get(nutriente)

            if valor_obtido is None:
                erros.append(f"Nutriente {nutriente} não calculado")
                continue

            # Tolerância maior para igualdade, menor para desigualdade
            tol = TOLERANCIA_IGUALDADE_NUTRIENTE if operador == '=' else TOLERANCIA_PERCENTUAL

            if not validar_atendimento_restricao(
                valor_obtido, valor_exigido, operador, tol
            ):
                restricoes_violadas.append({
                    'nutriente': nutriente,
                    'operador': operador,
                    'exigido': valor_exigido,
                    'obtido': valor_obtido,
                    'diferenca': valor_obtido - valor_exigido,
                })

        if restricoes_violadas:
            erros.append(
                f"Restrições nutricionais violadas: {len(restricoes_violadas)} nutriente(s)"
            )

        # 4. Levanta exceção se há erros críticos
        if erros:
            raise SolucaoInvalidaError(
                f"Solução inválida: {'; '.join(erros)}"
            )

        return {
            'valida': True,
            'avisos': avisos,
            'restricoes_violadas': restricoes_violadas,
        }

    def calcular_detalhes_nutrientes(self, x, ingredientes_dados, restricoes):
        """
        Calcula detalhes de nutrientes obtidos vs exigidos.

        Args:
            x: dict {ingrediente_id: proporcao}
            ingredientes_dados: dict {ingrediente_id: {pb: X, ndt: Y, ...}}
            restricoes: list [{nutriente, operador, valor}, ...]

        Returns:
            dict com nutrientes obtidos e validação
        """
        nutrientes_totais = calcular_nutrientes_totais(x, ingredientes_dados)

        detalhes = []
        for restricao in restricoes:
            nutriente = restricao['nutriente']
            valor_exigido = restricao['valor']
            operador = restricao['operador']
            valor_obtido = nutrientes_totais.get(nutriente, 0.0)

            tol = TOLERANCIA_IGUALDADE_NUTRIENTE if operador == '=' else TOLERANCIA_PERCENTUAL
            atende = validar_atendimento_restricao(
                valor_obtido, valor_exigido, operador, tol
            )

            detalhes.append({
                'nutriente': nutriente,
                'operador': operador,
                'valor_exigido': round(valor_exigido, 4),
                'valor_obtido': round(valor_obtido, 4),
                'margem': round(valor_obtido - valor_exigido, 4),
                'atende': atende,
            })

        return detalhes
