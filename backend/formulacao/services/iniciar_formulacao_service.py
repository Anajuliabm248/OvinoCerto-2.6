"""
Application Service - IniciarFormulacaoService.

Primeira etapa do fluxo de criação (seção 6, passos 1-2 do documento
de arquitetura): usuário escolhe propriedade + lote, e em seguida
ESCOLHE explicitamente qual ExigenciaNRC usar como ponto de partida
(ver formulacao/api/listagem_exigencias_nrc.py para a listagem
sugerida/paginada exibida ao usuário antes desta chamada).

Diferente da versão anterior, este service NÃO faz lookup automático
por categoria/fase/peso/GMD — o usuário decide, com o sistema apenas
sugerindo as opções mais aderentes ao lote em primeiro lugar.

Cria Formulacao (RASCUNHO) + ExigenciaConfigurada (cópia editável da
ExigenciaNRC escolhida) + ConfiguracaoNutriente para cada nutriente.

NÃO cria ingredientes nem gera distribuição inicial — isso é
responsabilidade de GerarFormulacaoInicialService.
"""

from __future__ import annotations

from django.db import transaction

from exigencia_nrc.models import ExigenciaNRC
from formulacao.models import Formulacao, StatusFormulacao
from formulacao.repositories import ExigenciaRepository
from lote.models import Lote


class IniciarFormulacaoService:

    @staticmethod
    @transaction.atomic
    def executar(
        lote_id: int,
        exigencia_nrc_id: int,
        usuario_id: int,
        titulo: str,
        observacoes: str = "",
    ) -> Formulacao:
        """
        lote_id          : lote já cadastrado pelo usuário.
        exigencia_nrc_id : ExigenciaNRC escolhida explicitamente pelo
                           usuário na tela de seleção (listagem
                           sugerida + "ver mais" paginado).
        """
        try:
            lote = Lote.objects.select_related("propriedade__usuario").get(pk=lote_id)
        except Lote.DoesNotExist:
            raise ValueError(f"Lote {lote_id} não encontrado.")

        if lote.propriedade.usuario_id != usuario_id:
            raise ValueError("Você não tem permissão para formular este lote.")

        try:
            exigencia_nrc = ExigenciaNRC.objects.get(pk=exigencia_nrc_id)
        except ExigenciaNRC.DoesNotExist:
            raise ValueError(f"ExigenciaNRC {exigencia_nrc_id} não encontrada.")

        if exigencia_nrc.cms_kg is None or exigencia_nrc.cms_kg <= 0:
            raise ValueError(
                f"A exigência NRC selecionada (id={exigencia_nrc_id}) não possui "
                "CMS (kg/dia) definido. Escolha outra exigência ou complete o "
                "cadastro da tabela NRC."
            )

        formulacao = Formulacao.objects.create(
            lote_id=lote_id,
            usuario_id=usuario_id,
            titulo=titulo,
            observacoes=observacoes,
            status=StatusFormulacao.RASCUNHO,
        )

        ExigenciaRepository.criar_de_nrc(
            formulacao=formulacao,
            exigencia_nrc=exigencia_nrc,
            cms_kg=float(exigencia_nrc.cms_kg),
        )

        return formulacao
