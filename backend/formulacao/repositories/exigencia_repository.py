"""
Exigencia configurada

Traduz entre os models Django (ExigenciaConfigurada,
ConfiguracaoNutriente, HistoricoConfiguracaoNutriente) e os
objetos de domínio (RequisitoNutriente).

Responsabilidades:
- Construir dict[Nutriente, RequisitoNutriente] a partir do banco.
- Criar ExigenciaConfigurada + ConfiguracaoNutriente a partir de
  um registro ExigenciaNRC (momento da criação da formulação).
- Gravar alterações individuais de nutriente + log de histórico.
"""

from __future__ import annotations

import datetime

from django.db import transaction

from exigencia_nrc.models import ExigenciaNRC
from formulacao.domain.nutrientes import Nutriente
from formulacao.domain.requisito import Operador, RequisitoNutriente
from formulacao.models import (
    ConfiguracaoNutriente,
    ExigenciaConfigurada,
    Formulacao,
    HistoricoConfiguracaoNutriente,
)


class ExigenciaRepository:

    

    @staticmethod
    def get_requisitos(formulacao_id: int) -> dict[Nutriente, RequisitoNutriente]:
        """
        Carrega os ConfiguracaoNutriente de uma formulação e constrói
        o dict {Nutriente: RequisitoNutriente} usado pelo MotorRecalculo.

        Retorna vazio se ExigenciaConfigurada não existir ainda
        (formulação em estado RASCUNHO antes da seleção de exigências).
        """
        try:
            exigencia = ExigenciaConfigurada.objects.get(formulacao_id=formulacao_id)
        except ExigenciaConfigurada.DoesNotExist:
            return {}

        qs = ConfiguracaoNutriente.objects.filter(
            exigencia_configurada=exigencia
        ).values("nutriente", "operador", "valor_min", "valor_max",
                 "valor_origem_nrc", "alterado_pelo_usuario")

        requisitos: dict[Nutriente, RequisitoNutriente] = {}
        for row in qs:
            try:
                nutriente = Nutriente(row["nutriente"])
                operador  = Operador(row["operador"])
            except ValueError:
                # Nutriente ou operador desconhecido (dados legados):
                # ignorar silenciosamente para não quebrar o recálculo.
                continue

            kwargs = dict(
                valor_origem_nrc=row["valor_origem_nrc"],
                alterado_pelo_usuario=row["alterado_pelo_usuario"],
            )

            if operador == Operador.MAIOR_IGUAL:
                req = RequisitoNutriente.maior_igual(nutriente, row["valor_min"], **kwargs)
            elif operador == Operador.MENOR_IGUAL:
                req = RequisitoNutriente.menor_igual(nutriente, row["valor_max"], **kwargs)
            elif operador == Operador.ENTRE:
                req = RequisitoNutriente.entre(
                    nutriente, row["valor_min"], row["valor_max"], **kwargs
                )
            else:  # IGUAL
                # valor_min == valor_max == valor original;
                # RequisitoNutriente.igual aplica a tolerância.
                req = RequisitoNutriente.igual(nutriente, row["valor_min"], **kwargs)

            requisitos[nutriente] = req

        return requisitos

    @staticmethod
    def get_cms_kg(formulacao_id: int) -> float | None:
        """CMS (kg/dia) armazenado na ExigenciaConfigurada."""
        try:
            return ExigenciaConfigurada.objects.values_list(
                "cms_kg", flat=True
            ).get(formulacao_id=formulacao_id)
        except ExigenciaConfigurada.DoesNotExist:
            return None

    
    # Escrita: criação a partir de ExigenciaNRC
    

    @staticmethod
    @transaction.atomic
    def criar_de_nrc(
        formulacao: Formulacao,
        exigencia_nrc: ExigenciaNRC,
        cms_kg: float,
    ) -> ExigenciaConfigurada:
        """
        Cria ExigenciaConfigurada + ConfiguracaoNutriente para todos os
        nutrientes, copiando os valores padrão do NRC.

        Todos os nutrientes nascem com alterado_pelo_usuario=False.

        Valores NRC estão em percentual (0-100 da MS) — nenhuma
        conversão necessária (ConfiguracaoNutriente também armazena
        em % da MS).
        """
        exigencia = ExigenciaConfigurada.objects.create(
            formulacao=formulacao,
            exigencia_nrc_origem=exigencia_nrc,
            cms_kg=cms_kg,
        )

        # (nutriente_db, operador, valor_min, valor_max, valor_origem_nrc)
        configs = [
            ("PB",  Operador.MAIOR_IGUAL, exigencia_nrc.pb,  None,              exigencia_nrc.pb),
            ("NDT", Operador.MAIOR_IGUAL, exigencia_nrc.ndt, None,              exigencia_nrc.ndt),
            ("FDN", Operador.MENOR_IGUAL, None,              exigencia_nrc.fdn, exigencia_nrc.fdn),
            ("EE",  Operador.MAIOR_IGUAL, exigencia_nrc.ee,  None,              exigencia_nrc.ee),
            ("CA",  Operador.MAIOR_IGUAL, exigencia_nrc.ca,  None,              exigencia_nrc.ca),
            ("P",   Operador.MAIOR_IGUAL, exigencia_nrc.p,   None,              exigencia_nrc.p),
        ]

        ConfiguracaoNutriente.objects.bulk_create([
            ConfiguracaoNutriente(
                exigencia_configurada=exigencia,
                nutriente=nutriente,
                operador=operador.value,
                valor_min=valor_min,
                valor_max=valor_max,
                valor_origem_nrc=valor_origem_nrc,
                alterado_pelo_usuario=False,
            )
            for nutriente, operador, valor_min, valor_max, valor_origem_nrc in configs
        ])

        return exigencia

    
    # Escrita: atualização de nutriente individual
    

    @staticmethod
    @transaction.atomic
    def atualizar_nutriente(
        formulacao_id: int,
        nutriente: Nutriente,
        operador: Operador,
        valor_min: float | None,
        valor_max: float | None,
        usuario_id: int | None = None,
    ) -> ConfiguracaoNutriente:
        """
        Atualiza o operador/limites de um nutriente e registra o
        histórico de alteração.

        Chamado pelo Application Service após validação de domínio
        (o service garante valor_min < valor_max para ENTRE, etc.).
        """
        config = ConfiguracaoNutriente.objects.select_for_update().get(
            exigencia_configurada__formulacao_id=formulacao_id,
            nutriente=nutriente.value,
        )

        # Gravar histórico antes de alterar
        HistoricoConfiguracaoNutriente.objects.create(
            configuracao=config,
            usuario_id=usuario_id,
            operador_anterior=config.operador,
            valor_min_anterior=config.valor_min,
            valor_max_anterior=config.valor_max,
            operador_novo=operador.value,
            valor_min_novo=valor_min,
            valor_max_novo=valor_max,
        )

        config.operador              = operador.value
        config.valor_min             = valor_min
        config.valor_max             = valor_max
        config.alterado_pelo_usuario = True
        config.save(update_fields=[
            "operador", "valor_min", "valor_max",
            "alterado_pelo_usuario", "dt_alteracao",
        ])

        return config