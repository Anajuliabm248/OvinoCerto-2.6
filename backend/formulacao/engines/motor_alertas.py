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
"""

from __future__ import annotations

from dataclasses import dataclass

from formulacao.domain.resultado import ResultadoAdequacao
from formulacao.domain.requisito import StatusAdequacao


@dataclass(frozen=True)
class ThresholdsSeveridade:
    info_max:    float = 0.05   # até 5%  → INFO
    atencao_max: float = 0.20   # até 20% → ATENCAO; acima → CRITICO

    soma_atencao_pp: float = 0.1  # ponto percentual de desvio → ATENCAO
    soma_critico_pp: float = 1.0  # ponto percentual de desvio → CRITICO


_DEFAULTS = ThresholdsSeveridade()


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
    def _severidade_nutricional(
        magnitude: float,
        thresholds: ThresholdsSeveridade,
    ) -> str:
        if magnitude <= thresholds.info_max:
            return "INFO"
        if magnitude <= thresholds.atencao_max:
            return "ATENCAO"
        return "CRITICO"