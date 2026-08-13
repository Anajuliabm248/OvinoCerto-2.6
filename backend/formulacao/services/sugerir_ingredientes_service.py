"""
Application Service - SugerirIngredientesService.

Fase F do roadmap (seção 20).

Carrega o último snapshot para obter ResultadoAdequacao e
vetor_total, monta os CandidatoSugestao a partir do catálogo e
delega ao MotorSugestao para ranking e projeção what-if.

Modos:
  adicionar  (padrão)
    candidatos = ingredientes NÃO presentes na formulação
    (sistema + custom do usuário).

  substituir
    candidatos = todos disponíveis EXCETO o próprio ingrediente
    substituído; vetor deste último é passado como referência para
    a distância euclidiana normalizada.
"""
from __future__ import annotations

import numpy as np
from django.db.models import Q

from formulacao.engines.motor_sugestao import (
    CandidatoSugestao,
    MotorSugestao,
    SugestaoIngrediente,
)
from formulacao.domain.nutrientes import NUTRIENTES_ORDEM, Nutriente, indice_de
from formulacao.models import IngredienteFormulacao
from formulacao.repositories import SnapshotRepository
from ingrediente.models import Ingrediente, PrecoIngredienteUsuario


class SugerirIngredientesService:
    """Reúne o contexto e ranqueia ingredientes permitidos ao usuário."""

    @staticmethod
    def executar(
        formulacao_id: int,
        usuario_id: int | None = None,
        modo: str = "adicionar",
        criterio: str = "nutricional",
        ing_form_id: int | None = None,
        max_resultados: int = 10,
    ) -> list[SugestaoIngrediente]:
        """
        Parâmetros
        ----------
        formulacao_id  : formulação cujo resultado será consultado.
        usuario_id     : perfil do usuário (para incluir ingredientes custom
                         e resolver o preço regional dele por candidato).
        modo           : 'adicionar' | 'substituir' — conjunto de candidatos.
        criterio       : 'nutricional' | 'custo_beneficio' — ordenação.
        ing_form_id    : ID do IngredienteFormulacao a substituir
                         (obrigatório em modo 'substituir').
        max_resultados : limite da lista retornada.
        """
        snapshot = SnapshotRepository.get_ultimo(formulacao_id)
        if snapshot is None:
            raise ValueError(
                "Formulação não possui resultado calculado. "
                "Gere a formulação inicial antes de pedir sugestões."
            )

        payload         = snapshot.payload
        desvios_payload = payload.get("resultado_adequacao", {}).get("desvios", [])
        vetor_total     = _dict_para_array(payload.get("vetor_total", {}))

        ids_presentes = set(
            IngredienteFormulacao.objects
            .filter(formulacao_id=formulacao_id, ingrediente__isnull=False)
            .values_list("ingrediente_id", flat=True)
        )

        vetor_substituido: np.ndarray | None = None
        fracao_substituido: float | None = None
        ids_excluir: set[int]

        if modo == "substituir":
            if ing_form_id is None:
                raise ValueError("Informe 'ing_form_id' para o modo 'substituir'.")
            try:
                ing_form = (
                    IngredienteFormulacao.objects
                    .select_related("ingrediente")
                    .get(pk=ing_form_id, formulacao_id=formulacao_id)
                )
            except IngredienteFormulacao.DoesNotExist:
                raise ValueError(
                    f"IngredienteFormulacao {ing_form_id} não encontrado "
                    f"na formulação {formulacao_id}."
                )
            if ing_form.ingrediente:
                vetor_substituido = _ingrediente_para_array(ing_form.ingrediente)
                fracao_substituido = float(ing_form.ms_porcent) / 100.0
                ids_excluir = {ing_form.ingrediente_id}
            else:
                ids_excluir = set()
        else:
            ids_excluir = ids_presentes

        qs = (
            Ingrediente.objects
            .filter(Q(fonte_valadares=True) | Q(usuario_id=usuario_id))
            .exclude(pk__in=ids_excluir)
            .order_by("classificacao", "tipo", "nome")
        )
        candidatos_ing = list(qs)

        precos_usuario = dict(
            PrecoIngredienteUsuario.objects
            .filter(usuario_id=usuario_id, ingrediente_id__in=[c.pk for c in candidatos_ing])
            .values_list("ingrediente_id", "preco_kg_mn")
        )

        candidatos = [
            CandidatoSugestao(
                ingrediente_id=ing.pk,
                nome=ing.nome,
                classificacao=ing.classificacao,
                tipo=ing.tipo,
                custo_kg=float(precos_usuario.get(ing.pk, 0.0)),
                ms_percentual=float(ing.ms or 0.0),
                vetor=_ingrediente_para_array(ing),
            )
            for ing in candidatos_ing
        ]

        return MotorSugestao.sugerir(
            desvios_payload=desvios_payload,
            candidatos=candidatos,
            vetor_total_atual=vetor_total,
            modo=modo,
            criterio=criterio,
            vetor_substituido=vetor_substituido,
            fracao_substituido=fracao_substituido,
            max_resultados=max_resultados,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ingrediente_para_array(ing: Ingrediente) -> np.ndarray:
    """Monta array canônico [PB, NDT, FDN, EE, CA, P, CA_P] em % MS."""
    v = np.zeros(len(NUTRIENTES_ORDEM), dtype=float)
    v[indice_de(Nutriente.PB)]  = float(ing.pb  or 0.0)
    v[indice_de(Nutriente.NDT)] = float(ing.ndt or 0.0)
    v[indice_de(Nutriente.FDN)] = float(ing.fdn or 0.0)
    v[indice_de(Nutriente.EE)]  = float(ing.ee  or 0.0)
    v[indice_de(Nutriente.CA)]  = float(ing.ca  or 0.0)
    v[indice_de(Nutriente.P)]   = float(ing.p   or 0.0)
    p_val = float(ing.p or 0.0)
    if p_val > 1e-9:
        v[indice_de(Nutriente.CA_P)] = float(ing.ca or 0.0) / p_val
    return v


def _dict_para_array(d: dict) -> np.ndarray:
    """Reconstrói array canônico a partir do dict do snapshot (vetor_total)."""
    v = np.zeros(len(NUTRIENTES_ORDEM), dtype=float)
    for i, nutriente in enumerate(NUTRIENTES_ORDEM):
        v[i] = float(d.get(nutriente.value, 0.0))
    return v
