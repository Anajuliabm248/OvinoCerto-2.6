"""Caso de uso para persistir a quantidade operacional da mistura."""

from __future__ import annotations

import math

from django.db import transaction

from formulacao.models import Formulacao
from formulacao.services.calcular_dados_dieta_service import (
    CalcularDadosDietaService,
)

# pylint: disable=no-member,too-few-public-methods


class AtualizarQuantidadeMisturaService:
    """Salva a quantidade em kg de MN e devolve os dados derivados atualizados."""

    @staticmethod
    @transaction.atomic
    def executar(
        formulacao_id: int,
        quantidade_mistura_mn_kg: float | None,
    ) -> dict:
        """Atualiza somente a quantidade operacional, sem gerar snapshot ou evento."""
        if quantidade_mistura_mn_kg is not None and (
            not math.isfinite(quantidade_mistura_mn_kg)
            or quantidade_mistura_mn_kg <= 0.0
        ):
            raise ValueError("Informe um valor finito e maior que zero.")

        try:
            formulacao = Formulacao.objects.select_for_update().get(
                pk=formulacao_id
            )
        except Formulacao.DoesNotExist:
            raise ValueError(
                f"Formulação {formulacao_id} não encontrada."
            ) from None

        formulacao.quantidade_mistura_mn_kg = quantidade_mistura_mn_kg
        formulacao.save(update_fields=["quantidade_mistura_mn_kg", "dt_alt"])

        return CalcularDadosDietaService.executar(formulacao_id=formulacao_id)
