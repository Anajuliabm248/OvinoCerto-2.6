"""
Repository - ExigenciaConfigurada / ConfiguracaoNutriente.

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

from django.db import transaction

from exigencia_nrc.models import ExigenciaNRC
from formulacao.domain.nutrientes import Nutriente
from formulacao.domain.requisito import Operador, RequisitoNutriente
from formulacao.engines.estimador_referencia import ContextoZootecnico
from formulacao.models import (
    ConfiguracaoNutriente,
    ExigenciaConfigurada,
    Formulacao,
    HistoricoConfiguracaoNutriente,
)


class ExigenciaRepository:
    """Traduz a exigência configurada no banco para objetos do domínio puro."""

    # ------------------------------------------------------------------
    # Leitura: DB → Domínio
    # ------------------------------------------------------------------

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

    @staticmethod
    def get_contexto_zootecnico(
        formulacao_id: int,
    ) -> ContextoZootecnico | None:
        """Contexto da linha NRC de origem usado apenas na estimativa inicial."""
        try:
            exigencia = (
                ExigenciaConfigurada.objects
                .select_related("exigencia_nrc_origem")
                .get(formulacao_id=formulacao_id)
            )
        except ExigenciaConfigurada.DoesNotExist:
            return None

        origem = exigencia.exigencia_nrc_origem
        if (
            origem is None
            or origem.pv_kg is None
            or origem.gmd_kg is None
            or exigencia.cms_kg is None
        ):
            return None
        return ContextoZootecnico(
            categoria=origem.categoria,
            fase=origem.fase,
            peso_vivo_kg=float(origem.pv_kg),
            gmd_kg=float(origem.gmd_kg),
            cms_kg=float(exigencia.cms_kg),
        )

    @staticmethod
    def serializar_configuracao(formulacao_id: int) -> dict | None:
        """
        Retorna a exigência configurada vigente em formato simples para
        ser gravada dentro do snapshot.
        """
        try:
            exigencia = (
                ExigenciaConfigurada.objects
                .select_related("exigencia_nrc_origem")
                .get(formulacao_id=formulacao_id)
            )
        except ExigenciaConfigurada.DoesNotExist:
            return None

        configs = (
            ConfiguracaoNutriente.objects
            .filter(exigencia_configurada=exigencia)
            .order_by("nutriente")
            .values(
                "nutriente",
                "operador",
                "valor_min",
                "valor_max",
                "valor_origem_nrc",
                "alterado_pelo_usuario",
                "dt_alteracao",
            )
        )

        return {
            "id": exigencia.id,
            "cms_kg": exigencia.cms_kg,
            "exigencia_nrc_origem_id": exigencia.exigencia_nrc_origem_id,
            "configuracoes": [
                {
                    **config,
                    "dt_alteracao": (
                        config["dt_alteracao"].isoformat()
                        if config["dt_alteracao"]
                        else None
                    ),
                }
                for config in configs
            ],
        }

    # ------------------------------------------------------------------
    # Escrita: criação a partir de ExigenciaNRC
    # ------------------------------------------------------------------

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

        Mapeamento NRC → operadores padrão:
        - PB, NDT, FDN, Ca, P, CA_P : ">=" (mínimo)
        - EE                        : "<=" (máximo)
        - Por default nenhum        : "="  (igual)

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
            ("PB",  Operador.MAIOR_IGUAL,  exigencia_nrc.pb_percentual,   None,                          exigencia_nrc.pb_percentual),
            ("NDT", Operador.MAIOR_IGUAL,  exigencia_nrc.ndt_percentual,  None,                          exigencia_nrc.ndt_percentual),
            ("FDN", Operador.MAIOR_IGUAL,  exigencia_nrc.fdn_percentual,  None,                          exigencia_nrc.fdn_percentual),
            ("EE",  Operador.MENOR_IGUAL,  None,                          exigencia_nrc.ee_percentual,   exigencia_nrc.ee_percentual),
            ("CA",  Operador.MAIOR_IGUAL,  exigencia_nrc.ca_percentual,   None,                          exigencia_nrc.ca_percentual),
            ("P",   Operador.MAIOR_IGUAL,  exigencia_nrc.p_percentual,    None,                          exigencia_nrc.p_percentual),
            ("CA_P", Operador.MAIOR_IGUAL, exigencia_nrc.ca_p_percentual, None,                          exigencia_nrc.ca_p_percentual),
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
            if valor_origem_nrc is not None
        ])

        return exigencia

    # ------------------------------------------------------------------
    # Escrita: atualização de nutriente individual
    # ------------------------------------------------------------------

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
