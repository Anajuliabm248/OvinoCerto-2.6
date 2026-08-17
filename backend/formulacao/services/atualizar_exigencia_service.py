"""
Application Service - AtualizarExigenciaService.

Permite ao usuário sobrescrever o operador/limites de UM nutriente
da ExigenciaConfigurada (seção 6, passo 2 do documento de arquitetura).

Validações de domínio (seção 16) antes de persistir:
- ENTRE exige valor_min < valor_max.
- MAIOR_IGUAL exige valor_min definido, valor_max ausente.
- MENOR_IGUAL exige valor_max definido, valor_min ausente.
- IGUAL exige um valor único (replicado em valor_min/valor_max pelo
  repositório, que aplica a tolerância numérica).

Regra de negócio: alterar a exigência configurada NÃO dispara
redistribuição automática das participações. Ela dispara apenas o
recálculo determinístico do resultado/alertas contra os novos limites,
gerando snapshot para manter a exigência configurada versionada.
"""

from __future__ import annotations

from django.db import transaction

from formulacao.domain.nutrientes import Nutriente
from formulacao.domain.requisito import Operador
from formulacao.models import ConfiguracaoNutriente, IngredienteFormulacao, TipoEvento
from formulacao.repositories import EventoRepository, ExigenciaRepository


class AtualizarExigenciaService:
    """Altera um requisito da cópia configurada e recalcula a formulação."""

    @staticmethod
    @transaction.atomic
    def executar(
        formulacao_id: int,
        nutriente: str,
        operador: str,
        valor: float | None = None,
        valor_min: float | None = None,
        valor_max: float | None = None,
        usuario_id: int | None = None,
    ) -> ConfiguracaoNutriente:
        """
        nutriente : código do nutriente (ex.: "PB", "FDN").
        operador  : "=" | ">=" | "<=" | "ENTRE".
        valor     : usado quando operador é "=" (define min=max=valor).
        valor_min / valor_max : usados conforme o operador.
        """
        try:
            nutriente_enum = Nutriente(nutriente)
        except ValueError:
            raise ValueError(f"Nutriente desconhecido: {nutriente}")

        try:
            operador_enum = Operador(operador)
        except ValueError:
            raise ValueError(f"Operador desconhecido: {operador}")

        vmin, vmax = AtualizarExigenciaService._normalizar_limites(
            operador_enum, valor, valor_min, valor_max
        )

        config = ExigenciaRepository.atualizar_nutriente(
            formulacao_id=formulacao_id,
            nutriente=nutriente_enum,
            operador=operador_enum,
            valor_min=vmin,
            valor_max=vmax,
            usuario_id=usuario_id,
        )

        EventoRepository.registrar(
            formulacao_id=formulacao_id,
            tipo_evento=TipoEvento.EXIGENCIA_ALTERADA,
            payload={
                "nutriente": nutriente_enum.value,
                "operador": operador_enum.value,
                "valor_min": vmin,
                "valor_max": vmax,
            },
            usuario_id=usuario_id,
        )

        tem_ingredientes = IngredienteFormulacao.objects.filter(
            formulacao_id=formulacao_id
        ).exists()
        if tem_ingredientes:
            from formulacao.services.recalcular_formulacao_service import (
                RecalcularFormulacaoService,
            )

            RecalcularFormulacaoService.executar(
                formulacao_id=formulacao_id,
                usuario_id=usuario_id,
                motivo=f"alteração de exigência: {nutriente_enum.value}",
            )

        return config

    @staticmethod
    def _normalizar_limites(
        operador: Operador,
        valor: float | None,
        valor_min: float | None,
        valor_max: float | None,
    ) -> tuple[float | None, float | None]:
        """
        Valida e normaliza a combinação de parâmetros recebidos da API
        para o par (valor_min, valor_max) esperado pelo repositório.

        Usa a tolerância do próprio RequisitoNutriente.igual() para
        operador "=" — aqui apenas validamos a presença dos valores;
        a tolerância numérica é aplicada na camada de domínio quando
        o requisito é reconstruído por ExigenciaRepository.get_requisitos().
        Por isso, para "=" persistimos valor_min == valor_max == valor.
        """
        if operador == Operador.IGUAL:
            if valor is None:
                raise ValueError("Operador '=' exige o campo 'valor'.")
            return valor, valor

        if operador == Operador.MAIOR_IGUAL:
            limite = valor if valor is not None else valor_min
            if limite is None:
                raise ValueError("Operador '>=' exige o campo 'valor' ou 'valor_min'.")
            return limite, None

        if operador == Operador.MENOR_IGUAL:
            limite = valor if valor is not None else valor_max
            if limite is None:
                raise ValueError("Operador '<=' exige o campo 'valor' ou 'valor_max'.")
            return None, limite

        if operador == Operador.ENTRE:
            if valor_min is None or valor_max is None:
                raise ValueError("Operador 'ENTRE' exige 'valor_min' e 'valor_max'.")
            if valor_min >= valor_max:
                raise ValueError(
                    f"Operador 'ENTRE' exige valor_min < valor_max "
                    f"(recebido min={valor_min}, max={valor_max})."
                )
            return valor_min, valor_max

        raise ValueError(f"Operador não tratado: {operador}")
