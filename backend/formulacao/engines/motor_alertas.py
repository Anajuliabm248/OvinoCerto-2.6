"""
Domínio puro - MotorAlertas.

Converte um ResultadoAdequacao em uma lista de dicts prontos para
AlertaRepository.upsert_alertas(). Sem I/O, sem Django.

Chamado ao final de todo pipeline do MotorRecalculo (seção 12).

Regras de severidade (configuráveis via thresholds):
  INFO    : magnitude_relativa <= 0.05  (desvio até 5%)
  ATENCAO : 0.05 < magnitude <= 0.20   (5% a 20%)
  CRITICO : magnitude > 0.20            (acima de 20%)

Alerta de SOMA (participações ≠ 100%):
  ATENCAO : desvio entre 0.1 e 1 ponto percentual
  CRITICO : desvio > 1 ponto percentual

Alerta de LIMITE_INGREDIENTE (participação de um ingrediente acima do
limite_max_participacao configurado no seu cadastro — ex.: bicarbonato
de sódio limitado a 1.5% da MS):
  Reaproveita os mesmos thresholds INFO/ATENCAO/CRITICO nutricionais,
  calculados sobre o quanto a participação atual ultrapassa o limite,
  proporcionalmente a ele (ex.: limite 2%, atual 2.5% → magnitude 0.25
  → ATENCAO). Nunca bloqueia — mesma filosofia dos alertas nutricionais:
  o valor travado manualmente pelo usuário pode ultrapassar o limite,
  apenas é sinalizado.
"""

from __future__ import annotations

from dataclasses import dataclass

from formulacao.domain.resultado import ResultadoAdequacao
from formulacao.domain.requisito import StatusAdequacao
from formulacao.engines.motor_custo import SaidaCusto


@dataclass(frozen=True)
class ThresholdsSeveridade:
    info_max:    float = 0.05   # até 5%  → INFO
    atencao_max: float = 0.20   # até 20% → ATENCAO; acima → CRITICO

    soma_atencao_pp: float = 0.1  # ponto percentual de desvio → ATENCAO
    soma_critico_pp: float = 1.0  # ponto percentual de desvio → CRITICO


_DEFAULTS = ThresholdsSeveridade()


@dataclass(frozen=True)
class ParticipacaoIngredienteLimite:
    """
    Estado de participação de UM ingrediente, pronto para ser avaliado
    contra seu limite_max_participacao (seção de limitação por
    ingrediente). Populado pelo Application Service a partir de
    IngredienteFormulacao + Ingrediente — o motor não conhece ORM.

    ingrediente_formulacao_id : id do IngredienteFormulacao (referência
                                 opaca, usada pelo AlertaRepository).
    ingrediente_nome          : nome para exibição/histórico do alerta.
    fracao_atual              : participação atual em 0-1 (não 0-100).
    limite_max                : limite configurado em 0-1, ou None se o
                                 ingrediente não tem limite cadastrado.
    """
    ingrediente_formulacao_id: int
    ingrediente_nome: str
    fracao_atual: float
    limite_max: float | None


class MotorAlertas:

    @staticmethod
    def avaliar(
        resultado: ResultadoAdequacao,
        thresholds: ThresholdsSeveridade = _DEFAULTS,
    ) -> list[dict]:
        """
        Retorna lista de dicts com a estrutura esperada por
        AlertaRepository.upsert_alertas():

          {
            "nutriente"          : str | None,
            "tipo"               : "DEFICIT" | "EXCESSO" | "SOMA",
            "severidade"         : "INFO" | "ATENCAO" | "CRITICO",
            "valor_atual"        : float,
            "valor_limite"       : float,
            "magnitude_relativa" : float,
          }

        Apenas desvios com status != ATENDE geram alertas.
        Soma inválida gera alerta adicional do tipo SOMA.
        """
        alertas: list[dict] = []

        
        # Alertas nutricionais (um por nutriente em déficit ou excesso)
        
        for desvio in resultado.desvios:
            if desvio.status == StatusAdequacao.ATENDE:
                continue

            tipo = desvio.status.value  # "DEFICIT" ou "EXCESSO"
            severidade = MotorAlertas._severidade_nutricional(
                desvio.magnitude_relativa, thresholds
            )

            # valor_limite: o limite que foi violado
            if desvio.status == StatusAdequacao.DEFICIT:
                valor_limite = desvio.requisito.valor_min or 0.0
            else:
                valor_limite = desvio.requisito.valor_max or 0.0

            alertas.append({
                "nutriente":           desvio.nutriente.value,
                "tipo":                tipo,
                "severidade":          severidade,
                "valor_atual":         round(desvio.valor_atual, 4),
                "valor_limite":        round(valor_limite, 4),
                "magnitude_relativa":  round(desvio.magnitude_relativa, 4),
            })

        
        # Alerta de soma de participações
        
        if not resultado.soma_valida:
            desvio_pp = resultado.desvio_soma_pontos_percentuais()
            if desvio_pp >= thresholds.soma_critico_pp:
                severidade = "CRITICO"
            else:
                severidade = "ATENCAO"

            alertas.append({
                "nutriente":           None,
                "tipo":                "SOMA",
                "severidade":          severidade,
                "valor_atual":         round(resultado.soma_participacoes * 100, 4),
                "valor_limite":        100.0,
                "magnitude_relativa":  round(desvio_pp / 100.0, 4),
            })

        return alertas

    @staticmethod
    def avaliar_limites_ingredientes(
        itens: list[ParticipacaoIngredienteLimite],
        thresholds: ThresholdsSeveridade = _DEFAULTS,
    ) -> list[dict]:
        """
        Retorna um alerta para cada ingrediente cuja participação atual
        (%MS) ultrapassa o limite_max_participacao configurado no
        cadastro (ex.: bicarbonato de sódio limitado a 1.5%).

        Ingredientes sem limite configurado (limite_max=None) ou dentro
        do limite não geram alerta. Nunca bloqueia a formulação — a
        participação pode ter sido travada manualmente pelo usuário
        acima do limite; aqui apenas sinalizamos (seção 15).

        Retorna dicts prontos para AlertaRepository.upsert_alertas(),
        com a mesma estrutura de MotorAlertas.avaliar() acrescida de
        "ingrediente_formulacao_id" e "ingrediente_nome":

          {
            "nutriente":                 None,
            "tipo":                      "LIMITE_INGREDIENTE",
            "severidade":                "INFO" | "ATENCAO" | "CRITICO",
            "valor_atual":               float (% MS),
            "valor_limite":              float (% MS),
            "magnitude_relativa":        float,
            "ingrediente_formulacao_id": int,
            "ingrediente_nome":          str,
          }
        """
        alertas: list[dict] = []

        for item in itens:
            if item.limite_max is None:
                continue
            if item.fracao_atual <= item.limite_max + 1e-9:
                continue

            if item.limite_max > 0:
                magnitude = (item.fracao_atual - item.limite_max) / item.limite_max
            else:
                # limite configurado como 0%: qualquer participação já é
                # uma violação total (evita divisão por zero).
                magnitude = 1.0

            severidade = MotorAlertas._severidade_nutricional(magnitude, thresholds)

            alertas.append({
                "nutriente":                 None,
                "tipo":                      "LIMITE_INGREDIENTE",
                "severidade":                severidade,
                "valor_atual":               round(item.fracao_atual * 100, 4),
                "valor_limite":              round(item.limite_max * 100, 4),
                "magnitude_relativa":        round(magnitude, 4),
                "ingrediente_formulacao_id": item.ingrediente_formulacao_id,
                "ingrediente_nome":          item.ingrediente_nome,
            })

        return alertas

    @staticmethod
    def avaliar_custo(saida_custo: SaidaCusto) -> list[dict]:
        """
        Gera um único alerta de severidade ATENCAO quando pelo menos um
        ingrediente da formulação não tem preço cadastrado (nem override
        local, nem catálogo geral) — os indicadores de custo
        (custo_ms_kg, custo_mn_kg, custo_animal_dia, custo_lote_dia)
        estão subestimados enquanto isso não for corrigido.

        Diferente dos alertas nutricionais, não há "magnitude" de desvio
        aqui — é um sinal binário (falta preço / não falta), por isso
        não reaproveita _severidade_nutricional.

        Retorna dict pronto para AlertaRepository.upsert_alertas(),
        mesma estrutura dos demais (nutriente=None, sem
        ingrediente_formulacao_id — o alerta é da formulação como um
        todo, não de uma linha específica, pois o MotorCusto não expõe
        QUAIS ingredientes estão sem preço, apenas que existe ao menos
        um).
        """
        if not saida_custo.tem_ingrediente_sem_preco:
            return []

        return [{
            "nutriente":           None,
            "tipo":                "CUSTO_INDISPONIVEL",
            "severidade":          "ATENCAO",
            "valor_atual":         0.0,
            "valor_limite":        0.0,
            "magnitude_relativa":  0.0,
        }]

    @staticmethod
    def _severidade_nutricional(
        magnitude: float,
        thresholds: ThresholdsSeveridade,
    ) -> str:
        if magnitude <= thresholds.info_max:
            return "INFO"
        if magnitude <= thresholds.atencao_max:
            return "ATENCAO"
        return "CRITICO"
