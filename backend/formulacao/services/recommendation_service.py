"""
Gerador de recomendações de ingredientes.
"""
import numpy as np
from ingrediente.models import Ingrediente


class RecommendationService:
    """Gera recomendações de ingredientes para melhoria da fórmula."""

    @staticmethod
    def gerar_recomendacoes(solucao, problema, inviavel=False):
        """
        Gera recomendações de ingredientes.

        Args:
            solucao: dict com x, nutrientes, custo
            problema: dict com ingredientes, restrições, etc.
            inviavel: bool, se True gera recomendações para viabilizar

        Returns:
            list de recomendações
        """
        recomendacoes = []

        if inviavel:
            recomendacoes.extend(
                RecommendationService._recomendacoes_inviavel(solucao, problema)
            )
        else:
            recomendacoes.extend(
                RecommendationService._recomendacoes_otimizacao(solucao, problema)
            )

        return recomendacoes[:5]  # Retornar top 5

    @staticmethod
    def _recomendacoes_inviavel(solucao, problema):
        """
        Recomendações quando o problema é inviável.

        Sugere ingredientes que poderiam "relaxar" restrições apertadas.
        """
        recomendacoes = []

        # Para cada restrição violada, sugerir ingredientes que ajudem
        restricoes_violadas = solucao.get('restricoes_violadas', [])

        for restricao_viol in restricoes_violadas:
            nutriente = restricao_viol['nutriente']
            operador = restricao_viol['operador']
            diferenca = restricao_viol.get('diferenca', 0)

            # Se operador é >=, precisa aumentar valor; se <=, precisa diminuir
            if operador == '>=' and diferenca < 0:
                # Precisa aumentar o nutriente
                recomendacoes.extend(
                    RecommendationService._buscar_ingredientes_por_nutriente_alto(
                        nutriente, problema, f"Aumentar {nutriente}"
                    )
                )
            elif operador == '<=' and diferenca > 0:
                # Precisa diminuir o nutriente
                recomendacoes.extend(
                    RecommendationService._buscar_ingredientes_por_nutriente_baixo(
                        nutriente, problema, f"Diminuir {nutriente}"
                    )
                )

        return recomendacoes

    @staticmethod
    def _recomendacoes_otimizacao(solucao, problema):
        """
        Recomendações para otimizar fórmula viável.

        Sugere ingredientes que melhoram custo ou nutrientes sem violar restrições.
        """
        recomendacoes = []

        x_atual = solucao.get('x', {})
        custo_atual = solucao.get('custo', 0)

        # Buscar ingredientes com melhor relação custo/benefício
        ingredientes_candidatos = [
            i for i in problema['ingredientes']
            if i.id not in x_atual or x_atual[i.id] < 5  # Não está muito presente
        ]

        if not ingredientes_candidatos:
            return recomendacoes

        # Ordenar por custo
        ingredientes_candidatos.sort(key=lambda i: i.custo_kg)

        for ing in ingredientes_candidatos[:5]:
            margem_custo = ((custo_atual - ing.custo_kg) / custo_atual) * 100 if custo_atual > 0 else 0

            if margem_custo < -5:  # Mais barato
                recomendacoes.append({
                    'tipo': 'substituicao_parcial',
                    'motivo': 'Reduzir custo',
                    'ingrediente_original': 'ingrediente mais caro',
                    'ingrediente_novo': ing.nome,
                    'economia_esperada': round(margem_custo, 2),
                    'pb': ing.pb,
                    'ndt': ing.ndt,
                    'fdn': ing.fdn,
                })

        return recomendacoes

    @staticmethod
    def _buscar_ingredientes_por_nutriente_alto(nutriente, problema, motivo):
        """
        Busca ingredientes com alto valor de um nutriente específico.
        """
        recomendacoes = []

        try:
            ingredientes_ordenados = sorted(
                problema['ingredientes'],
                key=lambda i: getattr(i, nutriente.lower(), 0),
                reverse=True
            )

            for ing in ingredientes_ordenados[:3]:
                valor = getattr(ing, nutriente.lower(), 0)
                recomendacoes.append({
                    'tipo': 'aumento_nutriente',
                    'motivo': motivo,
                    'ingrediente_sugerido': ing.nome,
                    'nutriente': nutriente,
                    'valor': valor,
                    'custo_kg': ing.custo_kg,
                })

        except Exception:
            pass

        return recomendacoes

    @staticmethod
    def _buscar_ingredientes_por_nutriente_baixo(nutriente, problema, motivo):
        """
        Busca ingredientes com baixo valor de um nutriente específico.
        """
        recomendacoes = []

        try:
            ingredientes_ordenados = sorted(
                problema['ingredientes'],
                key=lambda i: getattr(i, nutriente.lower(), 0),
                reverse=False
            )

            for ing in ingredientes_ordenados[:3]:
                valor = getattr(ing, nutriente.lower(), 0)
                recomendacoes.append({
                    'tipo': 'reducao_nutriente',
                    'motivo': motivo,
                    'ingrediente_sugerido': ing.nome,
                    'nutriente': nutriente,
                    'valor': valor,
                    'custo_kg': ing.custo_kg,
                })

        except Exception:
            pass

        return recomendacoes
