"""
Repository - ParametrosViabilidade.

Traduz entre o model Django e o MotorViabilidade (Quadros 9-14).
Único ponto que decide os valores default na primeira leitura (cópia
de Lote/ExigenciaConfigurada) — depois disso, os valores pertencem
inteiramente ao usuário; este repositório nunca sobrescreve um
registro já existente com dados atualizados do Lote/Exigência (ver
docstring do model ParametrosViabilidade).
"""

from __future__ import annotations

from django.db import transaction

from formulacao.models import ExigenciaConfigurada, Formulacao, ParametrosViabilidade

# Não há, hoje, um campo em Lote/ExigenciaConfigurada equivalente a
# "estimativa de permanência em dias" — é um dado puramente da
# simulação de custo (Quadro 10, Passos 15/16). 60 é só um chute
# inicial razoável para não deixar o campo vazio/zerado; o usuário
# ajusta no primeiro acesso à seção de custos.
_DEFAULT_ESTIMATIVA_PERMANENCIA_DIAS = 60

# Fallback só usado quando não é possível estimar cms_percentual_pv a
# partir de ExigenciaConfigurada.cms_kg (ex.: exigência ainda não
# configurada nesta formulação).
_DEFAULT_CMS_PERCENTUAL_PV_FALLBACK = 0.03

_CAMPOS_EDITAVEIS = frozenset({
    "num_animais",
    "gmd_esperado_kg",
    "estimativa_permanencia_dias",
    "peso_entrada_kg",
    "cms_percentual_pv",
    "perdas_alimentos_percentual",
    "preco_venda_kg_pv",
})


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

    # ------------------------------------------------------------------
    # Leitura-com-criação (default na primeira vez)
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def get_ou_criar_default(formulacao_id: int) -> ParametrosViabilidade:
        """
        Retorna o ParametrosViabilidade da formulação, criando com
        defaults copiados de Lote/ExigenciaConfigurada na primeira vez.

        Depois de criado, esta função NUNCA sobrescreve o registro
        existente — mesmo que o Lote ou a ExigenciaConfigurada mudem
        depois. É proposital: o requisito é "cópia editável
        independente", não "espelho ao vivo" (ver docstring do model).

        cms_percentual_pv é estimado como cms_kg / peso_vivo na
        criação — só como ponto de partida; o significado dos dois
        campos continua distinto depois (ver motor_viabilidade.py).
        """
        existente = (
            ParametrosViabilidade.objects
            .select_for_update()
            .filter(formulacao_id=formulacao_id)
            .first()
        )
        if existente is not None:
            return existente

        formulacao = (
            Formulacao.objects
            .select_related("lote")
            .get(id=formulacao_id)
        )
        lote = formulacao.lote

        cms_kg = (
            ExigenciaConfigurada.objects
            .filter(formulacao_id=formulacao_id)
            .values_list("cms_kg", flat=True)
            .first()
        )
        cms_percentual_pv = (
            cms_kg / lote.peso_vivo
            if cms_kg is not None and lote.peso_vivo and lote.peso_vivo > 0
            else _DEFAULT_CMS_PERCENTUAL_PV_FALLBACK
        )

        return ParametrosViabilidade.objects.create(
            formulacao=formulacao,
            num_animais=lote.num_animais,
            gmd_esperado_kg=lote.gmd_esperado,
            estimativa_permanencia_dias=_DEFAULT_ESTIMATIVA_PERMANENCIA_DIAS,
            peso_entrada_kg=lote.peso_vivo,
            cms_percentual_pv=cms_percentual_pv,
            perdas_alimentos_percentual=0.08,
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
