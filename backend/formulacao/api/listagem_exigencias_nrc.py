"""
Listagem de ExigenciaNRC para seleção pelo usuário.

Dois modos de consulta:

1. listar_sugeridas(lote): filtra por categoria + fase IGUAIS ao lote
   (o que mais frequentemente é o que o usuário quer), ordenado pela
   proximidade de peso vivo (pv_kg) e GMD (gmd_kg) em relação aos
   valores do lote — quanto mais perto, mais no topo da lista.

2. listar_todas(): catálogo completo, sem filtro de categoria/fase,
   para o caso "ver mais" — usado com paginação DRF (PageNumberPagination)
   na viewset, não aqui.

Nenhuma lógica de paginação nesta camada — apenas QuerySets prontos
para serem paginados ou serializados diretamente.
"""

from __future__ import annotations

from django.db.models import F, FloatField, Value
from django.db.models.functions import Abs

from exigencia_nrc.models import ExigenciaNRC
from lote.models import FASES_COM_PARTO_E_DIAS, Lote


def listar_sugeridas(lote: Lote):
    """
    QuerySet de ExigenciaNRC com mesma categoria e fase do lote,
    ordenado pela soma das distâncias absolutas de pv_kg e gmd_kg
    em relação aos valores do lote (mais aderente primeiro).

    Se o lote não tiver gmd_esperado definido (ex.: fases sem GMD
    aplicável), a distância de GMD é ignorada (tratada como 0).
    """
    qs = ExigenciaNRC.objects.filter(
        categoria=lote.categoria,
        fase=lote.fase,
    )
    if lote.fase in FASES_COM_PARTO_E_DIAS:
        if lote.tipo_parto and qs.filter(tipo_parto=lote.tipo_parto).exists():
            qs = qs.filter(tipo_parto=lote.tipo_parto)
        if lote.dias_fase and qs.filter(dias_fase=lote.dias_fase).exists():
            qs = qs.filter(dias_fase=lote.dias_fase)

    pv_lote = float(lote.peso_vivo) if lote.peso_vivo is not None else 0.0
    qs = qs.annotate(
        distancia_pv=Abs(F("pv_kg") - Value(pv_lote, output_field=FloatField())),
    )

    if lote.gmd_esperado is not None:
        gmd_lote = float(lote.gmd_esperado)
        qs = qs.annotate(
            distancia_gmd=Abs(
                F("gmd_kg") - Value(gmd_lote, output_field=FloatField())
            ),
        ).order_by(
            F("distancia_pv") + F("distancia_gmd"),
            "pv_kg",
        )
    else:
        qs = qs.order_by("distancia_pv", "pv_kg")

    return qs


def listar_todas():
    """
    Catálogo completo de ExigenciaNRC, para a tela "ver mais".
    Ordenação estável por categoria/fase/peso/GMD (Meta.ordering do
    model já cobre isso, mas é explicitado aqui por clareza).
    """
    return ExigenciaNRC.objects.all().order_by("categoria", "fase", "pv_kg", "gmd_kg")
