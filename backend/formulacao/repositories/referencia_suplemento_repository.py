"""Tradução das referências validadas do ORM para o domínio puro."""

from __future__ import annotations

from formulacao.engines.estimador_referencia import (
    ContextoZootecnico,
    IngredienteReferencia,
    ReferenciaSuplemento,
)
from formulacao.models import ReferenciaSuplementoValidada


class ReferenciaSuplementoRepository:
    """Entrega referências ativas sem levar modelos Django ao motor."""

    @staticmethod
    def listar_ativas() -> tuple[ReferenciaSuplemento, ...]:
        referencias = (
            ReferenciaSuplementoValidada.objects
            .filter(ativo=True)
            .prefetch_related("ingredientes")
            .order_by("categoria", "fase", "peso_vivo_kg", "gmd_kg", "codigo")
        )
        resultado = []
        for referencia in referencias:
            ingredientes = tuple(
                IngredienteReferencia(
                    classificacao=item.classificacao.upper(),
                    tipo=item.tipo.upper(),
                    participacao=item.participacao_pct_ms / 100.0,
                    composicao=(
                        item.pb_pct,
                        item.ndt_pct,
                        item.fdn_pct,
                        item.ee_pct,
                        item.ca_pct,
                        item.p_pct,
                    ),
                )
                for item in referencia.ingredientes.all()
            )
            resultado.append(ReferenciaSuplemento(
                contexto=ContextoZootecnico(
                    categoria=referencia.categoria,
                    fase=referencia.fase,
                    peso_vivo_kg=referencia.peso_vivo_kg,
                    gmd_kg=referencia.gmd_kg,
                    cms_kg=referencia.cms_kg,
                ),
                pb=referencia.pb_requisito_pct,
                ndt=referencia.ndt_requisito_pct,
                ca=referencia.ca_requisito_pct,
                p=referencia.p_requisito_pct,
                ca_p=referencia.ca_p_requisito,
                receita=tuple(item.participacao for item in ingredientes),
                codigo=referencia.codigo,
                ingredientes=ingredientes,
            ))
        return tuple(resultado)
