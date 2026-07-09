"""
MotorSugestao — seção 10 do documento de arquitetura.

Dois modos:
  adicionar  — candidatos externos ao conjunto atual; score por
               similaridade direcional ao vetor de necessidade
               (déficits/excessos da formulação corrente).
  substituir — candidatos para trocar um ingrediente existente;
               combina score direcional + distância euclidiana
               normalizada em relação ao ingrediente a substituir.

What-if: simula a inclusão de DELTA_FRAC (5 %) do candidato e projeta
os deltas por nutriente — sem I/O, sem persistência.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from formulacao.domain.nutrientes import NUTRIENTES_ORDEM, Nutriente, indice_de

# Índices fixos (atalhos legíveis)
_IDX_PB  = indice_de(Nutriente.PB)
_IDX_NDT = indice_de(Nutriente.NDT)
_IDX_FDN = indice_de(Nutriente.FDN)
_IDX_EE  = indice_de(Nutriente.EE)
_IDX_CA  = indice_de(Nutriente.CA)
_IDX_P   = indice_de(Nutriente.P)

# Nutrientes primários: exclui CA_P (derivado) nos cálculos de score/distância
_IDX_PRIMARIOS = [indice_de(n) for n in NUTRIENTES_ORDEM if n != Nutriente.CA_P]
_N_NUTRI = len(NUTRIENTES_ORDEM)


# ---------------------------------------------------------------------------
# DTOs de entrada e saída
# ---------------------------------------------------------------------------

@dataclass
class CandidatoSugestao:
    """Metadados + perfil nutricional de um ingrediente candidato."""
    ingrediente_id: int
    nome: str
    classificacao: str
    tipo: str
    custo_kg: float
    vetor: np.ndarray = field(repr=False)  # shape (_N_NUTRI,), em % MS


@dataclass
class SugestaoIngrediente:
    """Resultado de ranking para um candidato."""
    ingrediente_id: int
    nome: str
    classificacao: str
    tipo: str
    custo_kg: float
    # Composição
    pb: float
    ndt: float
    fdn: float
    ee: float
    ca: float
    p: float
    # Score e distância
    score: float
    distancia_euclidiana: float | None  # apenas em modo 'substituir'
    # Projeção what-if (delta % MS se DELTA_FRAC for incluído)
    delta_pb: float
    delta_ndt: float
    delta_fdn: float
    delta_ee: float
    delta_ca: float
    delta_p: float


# ---------------------------------------------------------------------------
# Motor
# ---------------------------------------------------------------------------

class MotorSugestao:
    """Motor puro de sugestão de ingredientes — sem I/O."""

    DELTA_FRAC: float = 0.05  # 5 % de participação na simulação what-if

    @classmethod
    def sugerir(
        cls,
        *,
        desvios_payload: list[dict],
        candidatos: list[CandidatoSugestao],
        vetor_total_atual: np.ndarray,
        modo: str = "adicionar",
        vetor_substituido: np.ndarray | None = None,
        max_resultados: int = 10,
    ) -> list[SugestaoIngrediente]:
        """
        Parâmetros
        ----------
        desvios_payload   : lista de dicts do snapshot (campo 'desvios'
                            dentro de 'resultado_adequacao').
        candidatos        : ingredientes candidatos para avaliação.
        vetor_total_atual : totais nutricionais da formulação atual (%MS).
        modo              : 'adicionar' | 'substituir'.
        vetor_substituido : vetor do ingrediente que será trocado
                            (obrigatório em modo 'substituir').
        max_resultados    : tamanho máximo da lista retornada.
        """
        if not candidatos:
            return []

        need_vec = cls._vetor_necessidade(desvios_payload)
        M = np.vstack([c.vetor for c in candidatos])  # (n_cand, n_nutri)

        scores = cls._calcular_scores(need_vec, M)

        if modo == "substituir" and vetor_substituido is not None:
            distancias = cls._distancias_euclidianas(M, vetor_substituido)
        else:
            distancias = [None] * len(candidatos)

        deltas = cls._calcular_deltas(M, vetor_total_atual)

        resultados: list[SugestaoIngrediente] = []
        for i, cand in enumerate(candidatos):
            v = cand.vetor
            resultados.append(SugestaoIngrediente(
                ingrediente_id=cand.ingrediente_id,
                nome=cand.nome,
                classificacao=cand.classificacao,
                tipo=cand.tipo,
                custo_kg=cand.custo_kg,
                pb=float(v[_IDX_PB]),
                ndt=float(v[_IDX_NDT]),
                fdn=float(v[_IDX_FDN]),
                ee=float(v[_IDX_EE]),
                ca=float(v[_IDX_CA]),
                p=float(v[_IDX_P]),
                score=float(scores[i]),
                distancia_euclidiana=(
                    float(distancias[i]) if distancias[i] is not None else None
                ),
                delta_pb=float(deltas[i, _IDX_PB]),
                delta_ndt=float(deltas[i, _IDX_NDT]),
                delta_fdn=float(deltas[i, _IDX_FDN]),
                delta_ee=float(deltas[i, _IDX_EE]),
                delta_ca=float(deltas[i, _IDX_CA]),
                delta_p=float(deltas[i, _IDX_P]),
            ))

        if modo == "substituir":
            resultados.sort(key=lambda s: (-s.score, s.distancia_euclidiana or 1e9))
        else:
            resultados.sort(key=lambda s: -s.score)

        return resultados[:max_resultados]

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @staticmethod
    def _vetor_necessidade(desvios_payload: list[dict]) -> np.ndarray:
        """
        Monta o vetor de necessidade a partir dos desvios do snapshot.

        DEFICIT  → magnitude positiva (queremos mais deste nutriente)
        EXCESSO  → magnitude negativa (queremos menos)
        ATENDE   → 0.0 (neutro)
        """
        v = np.zeros(_N_NUTRI, dtype=float)
        for d in desvios_payload:
            try:
                nutriente = Nutriente(d["nutriente"])
            except (KeyError, ValueError):
                continue
            if nutriente == Nutriente.CA_P:
                continue  # razão derivada, não entra no vetor diretamente
            idx = indice_de(nutriente)
            status = d.get("status", "ATENDE")
            magnitude = float(d.get("magnitude_relativa", 0.0))
            if status == "DEFICIT":
                v[idx] = magnitude
            elif status == "EXCESSO":
                v[idx] = -magnitude
        return v

    @staticmethod
    def _calcular_scores(need_vec: np.ndarray, M: np.ndarray) -> np.ndarray:
        """
        Score = produto escalar normalizado entre o vetor de necessidade
        e o perfil nutricional de cada candidato.

        Equivale a uma similaridade de cosseno direcionada:
        ingredientes que "puxam" os nutrientes deficitários para cima
        (e não agravam excessos) recebem score alto.

        Nutriente CA_P é excluído (derivado, indiretamente controlado).
        """
        need_sub = need_vec[_IDX_PRIMARIOS]
        M_sub = M[:, _IDX_PRIMARIOS]

        normas = np.linalg.norm(M_sub, axis=1)
        normas = np.where(normas < 1e-9, 1.0, normas)

        return (M_sub @ need_sub) / normas

    @staticmethod
    def _distancias_euclidianas(
        M: np.ndarray,
        vetor_ref: np.ndarray,
    ) -> np.ndarray:
        """
        Distância euclidiana normalizada entre cada candidato e o
        ingrediente de referência (o que está sendo substituído).

        A normalização escala cada dimensão para [0, 1] usando o range
        de todos os candidatos + referência — evita que nutrientes de
        maior magnitude (NDT ~70 %) dominem os de menor (Ca ~0.5 %).
        """
        M_sub  = M[:, _IDX_PRIMARIOS]
        ref_sub = vetor_ref[_IDX_PRIMARIOS]

        todos = np.vstack([M_sub, ref_sub.reshape(1, -1)])
        mn = todos.min(axis=0)
        mx = todos.max(axis=0)
        rng = np.where(mx - mn < 1e-9, 1.0, mx - mn)

        M_norm   = (M_sub  - mn) / rng
        ref_norm = (ref_sub - mn) / rng

        diffs = M_norm - ref_norm
        return np.sqrt((diffs ** 2).sum(axis=1))

    @classmethod
    def _calcular_deltas(
        cls,
        M: np.ndarray,
        vetor_total_atual: np.ndarray,
    ) -> np.ndarray:
        """
        Simulação what-if: inclui DELTA_FRAC do candidato diluindo o
        total atual.

          novo_total[i] = vetor_atual * (1 - d) + M[i] * d
          delta[i]      = novo_total[i] - vetor_atual

        Retorna array (n_cand, n_nutri).
        """
        d = cls.DELTA_FRAC
        total_scaled = vetor_total_atual * (1.0 - d)
        total_novo   = total_scaled + M * d          # broadcast (n_cand, n_nutri)
        return total_novo - vetor_total_atual