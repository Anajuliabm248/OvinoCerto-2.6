"""
Repository - Alerta.

Gerencia o ciclo de vida dos alertas nutricionais:
  gerado (resolvido=False) → resolvido (resolvido=True)

A cada recálculo, o Application Service chama `upsert_alertas()`,
que:
1. Marca como resolvidos todos os alertas ativos que NÃO aparecem
   no novo resultado (o problema foi corrigido).
2. Insere os alertas novos (que não existiam antes ou foram
   reabertos após resolução).

Alertas resolvidos NUNCA são deletados — preservam o histórico de
quando cada problema apareceu e quando foi corrigido (seção 12).
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from formulacao.models import Alerta


@transaction.atomic
def upsert_alertas(
    formulacao_id: int,
    novos: list[dict],
    versao_num: int,
) -> None:
    """
    novos: lista de dicts com as chaves:
      - nutriente       : str | None  (None para tipo SOMA)
      - tipo            : "DEFICIT" | "EXCESSO" | "SOMA"
      - severidade      : "INFO" | "ATENCAO" | "CRITICO"
      - valor_atual     : float
      - valor_limite    : float
      - magnitude_relativa : float

    versao_num: versão do snapshot gerado neste mesmo recálculo.
    """
    # Identifica quais (nutriente, tipo) estão ativos no novo resultado
    chaves_novas: set[tuple] = {
        (_normalizar(n["nutriente"]), n["tipo"]) for n in novos
    }

    
    # Passo 1: resolver alertas que não aparecem mais
    
    ativos = Alerta.objects.select_for_update().filter(
        formulacao_id=formulacao_id,
        resolvido=False,
    )
    para_resolver = []
    agora = timezone.now()
    for alerta in ativos:
        chave = (_normalizar(alerta.nutriente), alerta.tipo)
        if chave not in chaves_novas:
            alerta.resolvido = True
            alerta.snapshot_versao_resolucao = versao_num
            alerta.dt_resolucao = agora
            para_resolver.append(alerta)

    if para_resolver:
        Alerta.objects.bulk_update(
            para_resolver,
            fields=["resolvido", "snapshot_versao_resolucao", "dt_resolucao"],
        )

    
    # Passo 2: atualizar alertas persistentes e inserir alertas novos.
    # Se o mesmo alerta continua ativo em uma nova versão, mantemos a
    # versão de geração original, mas atualizamos severidade e valores.
    
    ativos_por_chave = {
        (_normalizar(alerta.nutriente), alerta.tipo): alerta
        for alerta in Alerta.objects.select_for_update().filter(
            formulacao_id=formulacao_id,
            resolvido=False,
        )
    }

    para_atualizar = []
    para_criar = []
    for n in novos:
        chave = (_normalizar(n["nutriente"]), n["tipo"])
        alerta_ativo = ativos_por_chave.get(chave)

        if alerta_ativo:
            alerta_ativo.severidade = n["severidade"]
            alerta_ativo.valor_atual = n["valor_atual"]
            alerta_ativo.valor_limite = n["valor_limite"]
            alerta_ativo.magnitude_relativa = n["magnitude_relativa"]
            para_atualizar.append(alerta_ativo)
        else:
            para_criar.append(
                Alerta(
                    formulacao_id=formulacao_id,
                    nutriente=n["nutriente"],
                    tipo=n["tipo"],
                    severidade=n["severidade"],
                    valor_atual=n["valor_atual"],
                    valor_limite=n["valor_limite"],
                    magnitude_relativa=n["magnitude_relativa"],
                    snapshot_versao_geracao=versao_num,
                    resolvido=False,
                )
            )

    if para_atualizar:
        Alerta.objects.bulk_update(
            para_atualizar,
            fields=[
                "severidade",
                "valor_atual",
                "valor_limite",
                "magnitude_relativa",
            ],
        )

    if para_criar:
        Alerta.objects.bulk_create(para_criar)


def _normalizar(valor: str | None) -> str:
    """Normaliza nutriente para chave de comparação (None → "")."""
    return valor or ""


class AlertaRepository:

    upsert = staticmethod(upsert_alertas)

    @staticmethod
    def listar_ativos(formulacao_id: int):
        return (
            Alerta.objects
            .filter(formulacao_id=formulacao_id, resolvido=False)
            .order_by("-severidade", "nutriente")
        )

    @staticmethod
    def listar_historico(formulacao_id: int):
        return (
            Alerta.objects
            .filter(formulacao_id=formulacao_id)
            .order_by("-dt_geracao")
        )
