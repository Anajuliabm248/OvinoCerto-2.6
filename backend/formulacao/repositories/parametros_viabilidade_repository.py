"""
Repository - ParametrosViabilidade.

Traduz entre o model Django e o MotorViabilidade (Quadros 9-14).
Único ponto que decide os valores default na primeira leitura. Quando
o contexto da exigência não corresponde ao lote, os campos herdados do
lote começam em zero e o CMS da exigência é convertido para percentual.
Valores já editados pelo usuário não são sobrescritos.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from formulacao.models import Formulacao, ParametrosViabilidade

# Não há, hoje, um campo em Lote/ExigenciaConfigurada equivalente a
# "estimativa de permanência em dias" — é um dado puramente da
# simulação de custo (Quadro 5). 30 é só um chute
# inicial razoável para não deixar o campo vazio/zerado; o usuário
# ajusta no primeiro acesso à seção de custos.
_DEFAULT_ESTIMATIVA_PERMANENCIA_DIAS = 30

_CAMPOS_EDITAVEIS = frozenset({
    "num_animais",
    "gmd_esperado_kg",
    "estimativa_permanencia_dias",
    "peso_entrada_kg",
    "cms_percentual_pv",
    "perdas_alimentos_percentual",
    "preco_venda_kg_pv",
})


@dataclass(frozen=True)
class ContextoViabilidade:
    """Dados de origem para inicializar e apresentar a simulação."""

    formulacao: Formulacao
    usa_dados_lote: bool
    categoria_display: str
    peso_vivo_kg: float
    raca: str | None
    sistema: str | None
    cms_kg: float | None
    peso_referencia_cms_kg: float


class ParametrosViabilidadeRepository:
    """Cria, recupera e atualiza o cenário econômico independente da receita."""

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    @staticmethod
    def get(formulacao_id: int) -> ParametrosViabilidade | None:
        """Retorna o registro existente, ou None se ainda não foi criado."""
        return (
            ParametrosViabilidade.objects
            .filter(formulacao_id=formulacao_id)
            .first()
        )

    @staticmethod
    def obter_contexto(formulacao_id: int) -> ContextoViabilidade:
        """Usa o lote apenas quando ele é compatível com a exigência escolhida."""
        formulacao = (
            Formulacao.objects
            .select_related("lote", "exigencia_configurada__exigencia_nrc_origem")
            .get(id=formulacao_id)
        )
        lote = formulacao.lote
        try:
            exigencia = formulacao.exigencia_configurada
        except ObjectDoesNotExist:
            exigencia = None

        origem = exigencia.exigencia_nrc_origem if exigencia else None
        if origem is not None and not ParametrosViabilidadeRepository._exigencia_corresponde_lote(
            lote, origem
        ):
            return ContextoViabilidade(
                formulacao=formulacao,
                usa_dados_lote=False,
                categoria_display=origem.get_categoria_display(),
                peso_vivo_kg=origem.pv_kg,
                raca=None,
                sistema=None,
                cms_kg=exigencia.cms_kg,
                peso_referencia_cms_kg=origem.pv_kg,
            )

        return ContextoViabilidade(
            formulacao=formulacao,
            usa_dados_lote=True,
            categoria_display=lote.get_categoria_display(),
            peso_vivo_kg=lote.peso_vivo,
            raca=lote.raca,
            sistema=lote.sistema,
            cms_kg=exigencia.cms_kg if exigencia else None,
            peso_referencia_cms_kg=lote.peso_vivo,
        )

    # ------------------------------------------------------------------
    # Leitura-com-criação (default na primeira vez)
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def get_ou_criar_default(formulacao_id: int) -> ParametrosViabilidade:
        """
        Retorna o ParametrosViabilidade da formulação, criando com
        defaults do lote quando a exigência corresponde a ele. Para
        exigência incompatível, zera os valores herdados do lote e usa
        cms_kg / pv_kg da exigência para preencher cms_percentual_pv.

        Um registro existente só é reinicializado se ainda refletir
        integralmente os valores do lote, preservando edições manuais.
        """
        existente = (
            ParametrosViabilidade.objects
            .select_for_update()
            .filter(formulacao_id=formulacao_id)
            .first()
        )
        contexto = ParametrosViabilidadeRepository.obter_contexto(formulacao_id)
        if existente is not None:
            if (
                not contexto.usa_dados_lote
                and ParametrosViabilidadeRepository._parametros_refletem_lote(
                    existente,
                    contexto.formulacao.lote,
                )
            ):
                ParametrosViabilidadeRepository._inicializar_sem_dados_lote(
                    existente,
                    contexto,
                )
            return existente

        cms_percentual_pv = ParametrosViabilidadeRepository._cms_percentual_do_contexto(
            contexto
        )

        return ParametrosViabilidade.objects.create(
            formulacao=contexto.formulacao,
            num_animais=(contexto.formulacao.lote.num_animais if contexto.usa_dados_lote else 0),
            gmd_esperado_kg=(contexto.formulacao.lote.gmd_esperado if contexto.usa_dados_lote else 0.0),
            estimativa_permanencia_dias=_DEFAULT_ESTIMATIVA_PERMANENCIA_DIAS,
            peso_entrada_kg=(contexto.formulacao.lote.peso_vivo if contexto.usa_dados_lote else 0.0),
            cms_percentual_pv=cms_percentual_pv,
            perdas_alimentos_percentual=0.1,
            preco_venda_kg_pv=None,
        )

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def atualizar(formulacao_id: int, **campos) -> ParametrosViabilidade:
        """
        Atualiza só os campos informados (partial update).

        Chamado pelo Application Service após validação de domínio
        (ranges, tipos etc.) — este método só valida que os nomes de
        campo são conhecidos; não valida valores.

        Campos aceitos: num_animais, gmd_esperado_kg,
        estimativa_permanencia_dias, peso_entrada_kg,
        cms_percentual_pv, perdas_alimentos_percentual,
        preco_venda_kg_pv.
        """
        desconhecidos = set(campos) - _CAMPOS_EDITAVEIS
        if desconhecidos:
            raise ValueError(f"Campos desconhecidos: {sorted(desconhecidos)}")

        parametros = ParametrosViabilidadeRepository.get_ou_criar_default(formulacao_id)
        for campo, valor in campos.items():
            setattr(parametros, campo, valor)

        parametros.save(update_fields=[*campos.keys(), "dt_alteracao"])
        return parametros

    @staticmethod
    def _exigencia_corresponde_lote(lote, exigencia_nrc) -> bool:
        """Compara o contexto produtivo, sem exigir o mesmo peso ou GMD."""
        return (
            exigencia_nrc.categoria == lote.categoria
            and exigencia_nrc.fase == lote.fase
            and exigencia_nrc.tipo_parto == lote.tipo_parto
        )

    @staticmethod
    def _cms_percentual_do_contexto(contexto: ContextoViabilidade) -> float:
        """Converte CMS kg/dia da exigência para a fração do peso de referência."""
        if (
            contexto.cms_kg is not None
            and contexto.cms_kg > 0
            and contexto.peso_referencia_cms_kg > 0
        ):
            return contexto.cms_kg / contexto.peso_referencia_cms_kg
        return 0.0

    @staticmethod
    def _parametros_refletem_lote(parametros, lote) -> bool:
        """Evita apagar valores que o usuário já alterou manualmente."""
        return (
            parametros.num_animais == lote.num_animais
            and isclose(parametros.gmd_esperado_kg, lote.gmd_esperado)
            and isclose(parametros.peso_entrada_kg, lote.peso_vivo)
        )

    @staticmethod
    def _inicializar_sem_dados_lote(
        parametros: ParametrosViabilidade,
        contexto: ContextoViabilidade,
    ) -> None:
        """Remove o preenchimento herdado do lote para exigência incompatível."""
        parametros.num_animais = 0
        parametros.gmd_esperado_kg = 0.0
        parametros.peso_entrada_kg = 0.0
        parametros.cms_percentual_pv = (
            ParametrosViabilidadeRepository._cms_percentual_do_contexto(contexto)
        )
        parametros.preco_venda_kg_pv = None
        parametros.save(update_fields=[
            "num_animais",
            "gmd_esperado_kg",
            "peso_entrada_kg",
            "cms_percentual_pv",
            "preco_venda_kg_pv",
            "dt_alteracao",
        ])
