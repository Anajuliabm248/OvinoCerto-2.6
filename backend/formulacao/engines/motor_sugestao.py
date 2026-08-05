"""
MotorSugestao — seção 10 do documento de arquitetura + Fase 2 (custo).

Dois eixos independentes de configuração:

  modo (conjunto de candidatos)
    adicionar  — candidatos externos ao conjunto atual; score por
                 similaridade direcional ao vetor de necessidade
                 (déficits/excessos da formulação corrente).
    substituir — candidatos para trocar um ingrediente existente;
                 combina score direcional + distância euclidiana
                 normalizada em relação ao ingrediente a substituir.

  criterio (como rankear esse conjunto)
    nutricional     — ordena só pelo score direcional (comportamento
                       original, sem considerar preço).
    custo_beneficio — ordena por indice_custo_beneficio = score /
                       custo_kg_ms. Só faz sentido dividir quando o
                       candidato de fato "puxa" na direção certa
                       (score > 0) — um ingrediente barato que agrava
                       um excesso não deve subir no ranking por ser
                       barato. Candidatos sem score positivo ou sem
                       preço/MS conhecidos ficam com
                       indice_custo_beneficio=None e vão para o fim
                       da lista, nunca excluídos silenciosamente.

custo_kg_ms é sempre calculado e exposto no resultado (mesmo em modo
'nutricional'), pois é informação útil para o usuário decidir — só a
ORDENAÇÃO muda de acordo com `criterio`.

What-if: simula a inclusão de DELTA_FRAC (5 %) do candidato e projeta
os deltas por nutriente — sem I/O, sem persistência.
"""
from __future__ import annotations

import math
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

CRITERIO_NUTRICIONAL     = "nutricional"
CRITERIO_CUSTO_BENEFICIO = "custo_beneficio"


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
    custo_kg: float          # R$/kg de matéria natural (MN); 0.0 = sem preço
    ms_percentual: float     # MS (%), usado para converter custo MN -> MS
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
    # Score nutricional (sempre calculado, independente do critério de ordenação)
    score: float
    distancia_euclidiana: float | None  # apenas em modo 'substituir'
    # Custo-benefício (None quando sem preço/MS conhecidos, ou score <= 0)
    custo_kg_ms: float | None
    indice_custo_beneficio: float | None
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

    # Ingredientes cujo perfil nutricional rastreado (PB/NDT/FDN/EE/Ca/P)
    # é inteiro (ou quase) zero — ex.: bicarbonato de sódio, calcário
    # calcítico puro — não são candidatos válidos para sugestão
    # NUTRICIONAL: eles não corrigem déficit nenhum, apenas não pioram
    # nada, o que lhes dá score == 0.0. Um score exatamente neutro
    # supera qualquer candidato que realmente contribua mas agrave
    # algum outro nutriente em excesso (score negativo) — um "não
    # fazer nada" vence um "fazer algo com efeito colateral", o que é
    # nutricionalmente sem sentido: aditivos de tamponamento/mineral
    # puro servem a um propósito completamente diferente (regulagem de
    # pH ruminal, fonte de NPN) que este motor não avalia. Excluídos
    # aqui, em vez de deixados para o usuário perceber a sugestão
    # absurda.
    NORMA_MINIMA_RELEVANTE: float = 1.0  # em % da MS (norma do subvetor primário)

    @classmethod
    def sugerir(
        cls,
        *,
        desvios_payload: list[dict],
        candidatos: list[CandidatoSugestao],
        vetor_total_atual: np.ndarray,
        modo: str = "adicionar",
        criterio: str = CRITERIO_NUTRICIONAL,
        vetor_substituido: np.ndarray | None = None,
        fracao_substituido: float | None = None,
        max_resultados: int = 10,
    ) -> list[SugestaoIngrediente]:
        """
        Parâmetros
        ----------
        desvios_payload   : lista de dicts do snapshot (campo 'desvios'
                            dentro de 'resultado_adequacao').
        candidatos        : ingredientes candidatos para avaliação.
        vetor_total_atual : totais nutricionais da formulação atual (%MS).
        modo              : 'adicionar' | 'substituir' — define o CONJUNTO
                            de candidatos avaliados E a mecânica de
                            simulação (ver abaixo).
        criterio          : 'nutricional' | 'custo_beneficio' — define a
                            ORDENAÇÃO do conjunto. Independente de `modo`
                            (pode combinar 'substituir' + 'custo_beneficio').
        vetor_substituido : vetor do ingrediente que será trocado
                            (obrigatório em modo 'substituir').
        fracao_substituido: fração 0-1 que o ingrediente substituído
                            ocupa HOJE na formulação (obrigatório em
                            modo 'substituir'). É o que faz a troca
                            depender de QUAL ingrediente está sendo
                            trocado — sem isso, trocar um ingrediente
                            que é 1% da dieta e um que é 50% dariam a
                            mesma simulação, o que não faz sentido.
        max_resultados    : tamanho máximo da lista retornada.

        Mecânica de simulação — modo='substituir'
        ------------------------------------------
        NÃO reaproveita a diluição de 'adicionar' (que simula "somar
        DELTA_FRAC=5% do candidato por cima de tudo"). Uma substituição
        é: tirar `fracao_substituido` do ingrediente original e pôr a
        MESMA fração do candidato no lugar. O efeito líquido é exato,
        não uma aproximação de 5%:

          delta_troca = fracao_substituido * (vetor_candidato - vetor_substituido)

        O score também passa a ser sobre esse delta real (quanto ele
        empurra a formulação na direção do que falta), não sobre o
        vetor bruto do candidato — isso é o que faz a pontuação levar
        em conta o que o ingrediente ATUAL está contribuindo: substituir
        um volumoso que fornece bastante NDT/PB por um mineral inerte
        aparece como um delta fortemente negativo nesses nutrientes
        (perda real), não como "neutro".
        """
        if not candidatos:
            return []

        eh_substituicao = modo == "substituir" and vetor_substituido is not None

        # O filtro de "candidato nutricionalmente inerte" só faz sentido
        # em 'adicionar': em 'substituir', o próprio delta_troca já
        # penaliza um candidato inerte (perde tudo que o original dava,
        # ganha nada) — filtrar aqui por norma bruta do candidato
        # excluiria trocas mineral-por-mineral legítimas.
        if not eh_substituicao:
            candidatos = cls._filtrar_candidatos_relevantes(candidatos)
            if not candidatos:
                return []

        need_vec = cls._vetor_necessidade(desvios_payload)
        M = np.vstack([c.vetor for c in candidatos])  # (n_cand, n_nutri)

        if eh_substituicao:
            fracao = fracao_substituido if fracao_substituido is not None else 0.0
            deltas = fracao * (M - vetor_substituido)   # efeito líquido real da troca
            scores = cls._calcular_scores(need_vec, deltas)
        else:
            scores = cls._calcular_scores(need_vec, M)
            deltas = cls._calcular_deltas(M, vetor_total_atual)

        custos_kg_ms = cls._custos_kg_ms(candidatos)
        indices_cb = cls._indices_custo_beneficio(scores, custos_kg_ms)

        if eh_substituicao:
            distancias = cls._distancias_euclidianas(M, vetor_substituido)
        else:
            distancias = [None] * len(candidatos)

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
                custo_kg_ms=(
                    None if np.isnan(custos_kg_ms[i]) else float(custos_kg_ms[i])
                ),
                indice_custo_beneficio=(
                    None if np.isnan(indices_cb[i]) else float(indices_cb[i])
                ),
                delta_pb=float(deltas[i, _IDX_PB]),
                delta_ndt=float(deltas[i, _IDX_NDT]),
                delta_fdn=float(deltas[i, _IDX_FDN]),
                delta_ee=float(deltas[i, _IDX_EE]),
                delta_ca=float(deltas[i, _IDX_CA]),
                delta_p=float(deltas[i, _IDX_P]),
            ))

        cls._ordenar(resultados, modo=modo, criterio=criterio)

        return resultados[:max_resultados]

    # ------------------------------------------------------------------
    # Filtro de relevância
    # ------------------------------------------------------------------

    @classmethod
    def _filtrar_candidatos_relevantes(
        cls,
        candidatos: list[CandidatoSugestao],
    ) -> list[CandidatoSugestao]:
        """
        Remove candidatos cujo perfil nutricional rastreado é
        essencialmente zero (norma abaixo de NORMA_MINIMA_RELEVANTE).

        Sem este filtro, um ingrediente inerte (ex.: bicarbonato de
        sódio, com PB=NDT=FDN=EE=Ca=P=0) recebe score == 0.0 — que
        supera qualquer candidato nutricionalmente ativo mas com score
        negativo (ex.: um grão que agrava um excesso já existente). Um
        "não contribui com nada" nunca deveria vencer um "contribui,
        mas com efeito colateral" numa sugestão NUTRICIONAL — são
        propósitos de formulação diferentes.
        """
        return [
            c for c in candidatos
            if float(np.linalg.norm(c.vetor[_IDX_PRIMARIOS])) >= cls.NORMA_MINIMA_RELEVANTE
        ]

    # ------------------------------------------------------------------
    # Ordenação
    # ------------------------------------------------------------------

    @staticmethod
    def _ordenar(
        resultados: list[SugestaoIngrediente],
        *,
        modo: str,
        criterio: str,
    ) -> None:
        """
        Ordena in-place.

        modo='adicionar': ordena só pela chave primária (score
        nutricional, ou índice de custo-benefício).

        modo='substituir': a chave primária é DIVIDIDA por
        (1 + distância euclidiana) — não é mais um desempate. Um
        candidato nutricionalmente ótimo mas muito diferente do
        ingrediente original (ex.: trocar um grão por um aditivo
        mineral) é penalizado proporcionalmente à distância; um
        candidato levemente pior nutricionalmente mas muito parecido
        (ex.: outro grão energético) sobe no ranking. Isso é o que
        torna "substituir" de fato uma sugestão de SUBSTITUTO, não
        apenas "o que mais corrige o desvio, não importa o quão
        diferente seja".

        Candidatos sem chave primária válida (indice_custo_beneficio
        None) vão para o final, nunca excluídos — mesmo com distância
        pequena, "sem informação de custo" não deve furar a fila.
        """
        if criterio == CRITERIO_CUSTO_BENEFICIO:
            chave_primaria = lambda s: (
                s.indice_custo_beneficio
                if s.indice_custo_beneficio is not None
                else -math.inf
            )
        else:
            chave_primaria = lambda s: s.score

        if modo == "substituir":
            def chave_final(s: SugestaoIngrediente) -> float:
                base = chave_primaria(s)
                if base == -math.inf:
                    return -math.inf
                distancia = s.distancia_euclidiana if s.distancia_euclidiana is not None else 0.0
                fator = 1.0 + distancia
                # Sign-safe: distância SEMPRE piora o resultado, nunca
                # melhora — dividir um score negativo por um fator > 1
                # o aproximaria de zero (pareceria "menos ruim"), o
                # que inverteria o efeito pretendido. Score >= 0 é
                # penalizado por divisão; score < 0 é penalizado por
                # multiplicação (fica mais negativo ainda).
                return base / fator if base >= 0 else base * fator

            resultados.sort(key=lambda s: -chave_final(s))
        else:
            resultados.sort(key=lambda s: -chave_primaria(s))

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
    def _custos_kg_ms(candidatos: list[CandidatoSugestao]) -> np.ndarray:
        """
        Converte custo_kg (R$/kg de MN) para R$/kg de MS por candidato:

          custo_kg_ms = custo_kg / (ms_percentual / 100)

        Retorna NaN quando custo_kg <= 0 (sem preço) ou ms_percentual
        <= 0 (dado ausente/inválido) — nunca ZeroDivisionError.
        """
        valores = np.full(len(candidatos), np.nan, dtype=float)
        for i, cand in enumerate(candidatos):
            if cand.custo_kg > 0 and cand.ms_percentual > 0:
                valores[i] = cand.custo_kg / (cand.ms_percentual / 100.0)
        return valores

    @staticmethod
    def _indices_custo_beneficio(
        scores: np.ndarray,
        custos_kg_ms: np.ndarray,
    ) -> np.ndarray:
        """
        indice_custo_beneficio = score / custo_kg_ms, apenas onde
        score > 0 (candidato realmente ajuda) E custo_kg_ms é
        conhecido e positivo. Nos demais casos, NaN — tratado como
        "sem informação suficiente para comparar por custo", não como
        pontuação zero (zero sugeriria "candidato ruim", o que nem
        sempre é verdade — só falta preço cadastrado).
        """
        indices = np.full_like(scores, np.nan, dtype=float)
        validos = (scores > 0) & ~np.isnan(custos_kg_ms) & (custos_kg_ms > 0)
        indices[validos] = scores[validos] / custos_kg_ms[validos]
        return indices

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
