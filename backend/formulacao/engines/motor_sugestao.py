"""
MotorSugestao — seção 10 do documento de arquitetura + Fase 2 (custo).

Dois eixos independentes de configuração:

  modo (conjunto de candidatos)
    adicionar  — candidatos externos ao conjunto atual; score por
                 similaridade direcional ao vetor de necessidade
                 (déficits/excessos da formulação corrente).
    substituir — candidatos para trocar um ingrediente existente;
                 filtra por função e combina necessidade, impacto real
                 da troca e distância euclidiana ponderada/normalizada.

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
import unicodedata
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
_IDX_CA_P = indice_de(Nutriente.CA_P)

# Nutrientes primários: exclui CA_P (derivado) nos cálculos de score/distância
_IDX_PRIMARIOS = [indice_de(n) for n in NUTRIENTES_ORDEM if n != Nutriente.CA_P]
_N_NUTRI = len(NUTRIENTES_ORDEM)

CRITERIO_NUTRICIONAL     = "nutricional"
CRITERIO_CUSTO_BENEFICIO = "custo_beneficio"

FUNCAO_ENERGETICO = "energetico"
FUNCAO_PROTEICO = "proteico"
FUNCAO_VOLUMOSO = "volumoso"
FUNCAO_FONTE_CA = "fonte_ca"
FUNCAO_FONTE_P = "fonte_p"
FUNCAO_FONTE_CA_P = "fonte_ca_p"
FUNCAO_TAMPONANTE = "tamponante"
FUNCAO_NPN = "npn"
FUNCAO_ADITIVO = "aditivo"
FUNCAO_DESCONHECIDA = "desconhecida"

# Escalas mínimas em % MS. Elas impedem que uma variação pequena de Ca/P
# domine a comparação só porque esses nutrientes têm números absolutos menores
# que PB/NDT/FDN. Quando o catálogo contém valores maiores, o próprio máximo
# observado passa a ser a escala daquela dimensão.
_ESCALAS_MINIMAS = np.array([20.0, 60.0, 40.0, 5.0, 1.0, 0.5], dtype=float)
_PESOS_BASE = np.array([1.20, 1.25, 1.00, 0.80, 1.35, 1.35], dtype=float)


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
    # Score nutricional composto (sempre calculado, independente do critério)
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
        candidato_substituido: CandidatoSugestao | None = None,
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
        candidato_substituido: metadados do ingrediente original, usados
                            apenas para identificar sua função nutricional.
                            É opcional para manter compatibilidade com os
                            chamadores antigos; sem ele, a função é inferida
                            somente pelo vetor nutricional.
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

        compatibilidades: np.ndarray | None = None
        funcao_substituido = FUNCAO_DESCONHECIDA
        if eh_substituicao:
            funcao_substituido = cls._classificar_funcao(
                candidato_substituido,
                vetor_fallback=vetor_substituido,
            )
            candidatos, compatibilidades = cls._filtrar_compativeis_substituicao(
                candidatos,
                funcao_substituido=funcao_substituido,
                candidato_substituido=candidato_substituido,
            )
            if not candidatos:
                return []

        M = np.vstack([c.vetor for c in candidatos])  # (n_cand, n_nutri)

        if eh_substituicao:
            fracao = fracao_substituido if fracao_substituido is not None else 0.0
            deltas = fracao * (M - vetor_substituido)   # efeito líquido real da troca
            scores_direcionais = cls._calcular_scores(need_vec, deltas)

            pesos_distancia = cls._pesos_distancia(
                need_vec,
                funcao_substituido=funcao_substituido,
            )
            distancias = cls._distancias_euclidianas(
                M,
                vetor_substituido,
                pesos=pesos_distancia,
            )
            impactos = cls._pontuar_impacto_troca(
                need_vec,
                deltas,
                vetor_total_atual,
            )
            scores = cls._scores_substituicao(
                need_vec=need_vec,
                candidatos=candidatos,
                M=M,
                compatibilidades=compatibilidades,
                distancias=distancias,
                scores_direcionais=scores_direcionais,
                impactos=impactos,
            )
            scores_ajuda_custo = impactos - 0.5
        else:
            scores = cls._calcular_scores(need_vec, M)
            deltas = cls._calcular_deltas(M, vetor_total_atual)
            distancias = [None] * len(candidatos)
            scores_ajuda_custo = scores

        custos_kg_ms = cls._custos_kg_ms(candidatos)
        indices_cb = cls._indices_custo_beneficio(
            scores,
            custos_kg_ms,
            scores_ajuda=scores_ajuda_custo,
        )

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
    # Compatibilidade funcional para substituições
    # ------------------------------------------------------------------

    @staticmethod
    def _normalizar_texto(valor: str) -> str:
        normalizado = unicodedata.normalize("NFKD", valor or "")
        return "".join(ch for ch in normalizado if not unicodedata.combining(ch)).lower()

    @classmethod
    def _classificar_funcao(
        cls,
        candidato: CandidatoSugestao | None,
        *,
        vetor_fallback: np.ndarray | None = None,
    ) -> str:
        """Deriva a função real usando nome, cadastro e composição."""
        if candidato is not None:
            nome = cls._normalizar_texto(candidato.nome)
            classificacao = cls._normalizar_texto(candidato.classificacao)
            tipo = cls._normalizar_texto(candidato.tipo)
            vetor = candidato.vetor
        else:
            nome = ""
            classificacao = ""
            tipo = ""
            vetor = vetor_fallback

        if vetor is None:
            vetor = np.zeros(_N_NUTRI, dtype=float)

        pb = float(vetor[_IDX_PB])
        ndt = float(vetor[_IDX_NDT])
        ca = float(vetor[_IDX_CA])
        p = float(vetor[_IDX_P])

        # Regras específicas vêm antes do tipo genérico cadastrado.
        if any(termo in nome for termo in ("bicarbonato", "tamponante", "buffer")):
            return FUNCAO_TAMPONANTE
        if "ureia" in nome or (pb >= 100.0 and ndt < 10.0):
            return FUNCAO_NPN
        if any(termo in nome for termo in ("ostra", "calcario", "calcareo")):
            return FUNCAO_FONTE_CA
        if "fosfato" in nome or "ossos" in nome:
            if ca >= 5.0 and p >= 5.0:
                return FUNCAO_FONTE_CA_P
            return FUNCAO_FONTE_P

        if classificacao == "volumoso" or tipo in {
            "forragens_secas", "forragens_verdes", "silagens",
        }:
            return FUNCAO_VOLUMOSO

        # A composição separa os diferentes papéis escondidos sob "mineral".
        if ca >= 10.0 and p >= 8.0:
            return FUNCAO_FONTE_CA_P
        if ca >= 10.0:
            return FUNCAO_FONTE_CA
        if p >= 8.0:
            return FUNCAO_FONTE_P
        if tipo == "proteico":
            return FUNCAO_PROTEICO
        if tipo == "energetico":
            return FUNCAO_ENERGETICO
        if tipo in {"aditivo", "aditivos", "mineral"}:
            return FUNCAO_ADITIVO

        # Fallback para ingredientes customizados com cadastro incompleto.
        if pb >= 20.0:
            return FUNCAO_PROTEICO
        if ndt >= 45.0:
            return FUNCAO_ENERGETICO
        if float(np.linalg.norm(vetor[_IDX_PRIMARIOS])) < 1e-9:
            return FUNCAO_ADITIVO
        return FUNCAO_DESCONHECIDA

    @classmethod
    def _filtrar_compativeis_substituicao(
        cls,
        candidatos: list[CandidatoSugestao],
        *,
        funcao_substituido: str,
        candidato_substituido: CandidatoSugestao | None,
    ) -> tuple[list[CandidatoSugestao], np.ndarray]:
        """Remove funções incompatíveis antes de qualquer distância."""
        compatibilidade_parcial = {
            FUNCAO_FONTE_CA: {FUNCAO_FONTE_CA_P: 0.65},
            FUNCAO_FONTE_P: {FUNCAO_FONTE_CA_P: 0.75},
            FUNCAO_FONTE_CA_P: {
                FUNCAO_FONTE_CA: 0.60,
                FUNCAO_FONTE_P: 0.70,
            },
        }

        filtrados: list[CandidatoSugestao] = []
        scores: list[float] = []
        for candidato in candidatos:
            funcao_candidato = cls._classificar_funcao(candidato)
            score = 0.0
            if funcao_candidato == funcao_substituido:
                score = 1.0
            else:
                score = compatibilidade_parcial.get(funcao_substituido, {}).get(
                    funcao_candidato,
                    0.0,
                )

            # Para cadastros customizados não classificáveis, preserva-se uma
            # saída conservadora: somente mesma classificação e mesmo tipo.
            if (
                score == 0.0
                and funcao_substituido == FUNCAO_DESCONHECIDA
                and candidato_substituido is not None
                and candidato.classificacao == candidato_substituido.classificacao
                and candidato.tipo == candidato_substituido.tipo
            ):
                score = 0.70

            if score > 0.0:
                filtrados.append(candidato)
                scores.append(score)

        return filtrados, np.asarray(scores, dtype=float)

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

        modo='substituir': o score já combina compatibilidade, distância
        ponderada, necessidade e impacto real da troca. A distância fica
        como desempate estável, evitando aplicá-la duas vezes ao ranking.

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
            resultados.sort(key=lambda s: (
                -chave_primaria(s),
                s.distancia_euclidiana if s.distancia_euclidiana is not None else math.inf,
            ))
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

    @classmethod
    def _pesos_distancia(
        cls,
        need_vec: np.ndarray,
        *,
        funcao_substituido: str,
    ) -> np.ndarray:
        """Combina pesos técnicos, função original e desvios atuais."""
        pesos = _PESOS_BASE.copy()
        pesos_funcao = {
            FUNCAO_ENERGETICO: {_IDX_NDT: 2.2, _IDX_EE: 1.4, _IDX_PB: 1.2},
            FUNCAO_PROTEICO: {_IDX_PB: 2.3, _IDX_NDT: 1.2},
            FUNCAO_VOLUMOSO: {_IDX_FDN: 2.3, _IDX_NDT: 1.3, _IDX_PB: 1.2},
            FUNCAO_FONTE_CA: {_IDX_CA: 3.0, _IDX_P: 1.5},
            FUNCAO_FONTE_P: {_IDX_P: 3.0, _IDX_CA: 1.4},
            FUNCAO_FONTE_CA_P: {_IDX_CA: 2.7, _IDX_P: 2.7},
            FUNCAO_NPN: {_IDX_PB: 3.0},
        }
        posicoes_primarias = {idx: pos for pos, idx in enumerate(_IDX_PRIMARIOS)}
        for idx, fator in pesos_funcao.get(funcao_substituido, {}).items():
            pesos[posicoes_primarias[idx]] *= fator

        necessidades = np.abs(need_vec[_IDX_PRIMARIOS])
        maior = float(necessidades.max()) if necessidades.size else 0.0
        if maior > 1e-12:
            pesos *= 1.0 + 2.0 * (necessidades / maior)

        # Mantém a escala da distância comparável entre diferentes chamadas.
        return pesos / float(pesos.mean())

    @classmethod
    def _scores_substituicao(
        cls,
        *,
        need_vec: np.ndarray,
        candidatos: list[CandidatoSugestao],
        M: np.ndarray,
        compatibilidades: np.ndarray,
        distancias: np.ndarray,
        scores_direcionais: np.ndarray,
        impactos: np.ndarray,
    ) -> np.ndarray:
        """Score composto do ranking, sempre no intervalo aproximado 0-1."""
        similaridade = 1.0 / (1.0 + distancias)
        direcao = 0.5 * (np.tanh(scores_direcionais) + 1.0)
        capacidade = cls._capacidade_corrigir_necessidade(
            need_vec,
            candidatos,
            M,
        )
        return (
            0.25 * compatibilidades
            + 0.25 * similaridade
            + 0.15 * direcao
            + 0.15 * capacidade
            + 0.20 * impactos
        )

    @classmethod
    def _capacidade_corrigir_necessidade(
        cls,
        need_vec: np.ndarray,
        candidatos: list[CandidatoSugestao],
        M: np.ndarray,
    ) -> np.ndarray:
        """Avalia função e teor do candidato para a necessidade dominante."""
        necessidades = np.abs(need_vec)
        if not np.any(necessidades > 1e-12):
            return np.full(len(candidatos), 0.5, dtype=float)

        idx = int(np.argmax(necessidades))
        sinal = 1.0 if need_vec[idx] >= 0 else -1.0
        funcoes_adequadas = {
            _IDX_PB: {FUNCAO_PROTEICO, FUNCAO_NPN},
            _IDX_NDT: {FUNCAO_ENERGETICO},
            _IDX_FDN: {FUNCAO_VOLUMOSO},
            _IDX_EE: {FUNCAO_ENERGETICO},
            _IDX_CA: {FUNCAO_FONTE_CA, FUNCAO_FONTE_CA_P},
            _IDX_P: {FUNCAO_FONTE_P, FUNCAO_FONTE_CA_P},
        }

        if idx == _IDX_CA_P:
            if sinal > 0:
                funcoes_alvo = {FUNCAO_FONTE_CA, FUNCAO_FONTE_CA_P}
            else:
                funcoes_alvo = {FUNCAO_FONTE_P, FUNCAO_FONTE_CA_P}
        else:
            funcoes_alvo = funcoes_adequadas.get(idx, set())

        escalas = cls._escalas_nutricionais(M, np.zeros(_N_NUTRI, dtype=float))
        resultados = np.zeros(len(candidatos), dtype=float)
        for i, candidato in enumerate(candidatos):
            funcao = cls._classificar_funcao(candidato)
            afinidade_funcional = 1.0 if funcao in funcoes_alvo else 0.20

            if idx == _IDX_CA_P:
                ca = max(float(M[i, _IDX_CA]), 0.0)
                p = max(float(M[i, _IDX_P]), 0.0)
                fornecimento = min((ca + p) / 5.0, 1.0)
                proporcao = ca / (ca + p) if sinal > 0 and ca + p > 1e-12 else 0.0
                if sinal < 0 and ca + p > 1e-12:
                    proporcao = p / (ca + p)
                perfil = fornecimento * proporcao
            else:
                pos = _IDX_PRIMARIOS.index(idx)
                teor_normalizado = min(max(float(M[i, idx]) / escalas[pos], 0.0), 1.0)
                perfil = teor_normalizado if sinal > 0 else 1.0 - teor_normalizado

            resultados[i] = 0.60 * afinidade_funcional + 0.40 * perfil
        return resultados

    @classmethod
    def _pontuar_impacto_troca(
        cls,
        need_vec: np.ndarray,
        deltas: np.ndarray,
        vetor_total_atual: np.ndarray,
    ) -> np.ndarray:
        """Mede quanto o delta real reduz ou agrava os desvios atuais."""
        if not np.any(np.abs(need_vec) > 1e-12):
            return np.full(deltas.shape[0], 0.5, dtype=float)

        escalas = cls._escalas_nutricionais(deltas, vetor_total_atual)
        necessidades = need_vec[_IDX_PRIMARIOS]
        denominador = max(float(np.abs(necessidades).sum()), 1e-12)
        impacto_bruto = (deltas[:, _IDX_PRIMARIOS] / escalas) @ necessidades
        impacto_bruto /= denominador

        necessidade_ca_p = float(need_vec[_IDX_CA_P])
        if abs(necessidade_ca_p) > 1e-12:
            ca_atual = float(vetor_total_atual[_IDX_CA])
            p_atual = float(vetor_total_atual[_IDX_P])
            razao_atual = ca_atual / p_atual if p_atual > 1e-12 else 0.0
            novo_ca = ca_atual + deltas[:, _IDX_CA]
            novo_p = p_atual + deltas[:, _IDX_P]
            nova_razao = np.divide(
                novo_ca,
                novo_p,
                out=np.zeros_like(novo_ca),
                where=np.abs(novo_p) > 1e-12,
            )
            delta_razao = (nova_razao - razao_atual) / max(abs(razao_atual), 1.0)
            peso_total = denominador + abs(necessidade_ca_p)
            impacto_bruto = (
                impacto_bruto * denominador
                + delta_razao * necessidade_ca_p
            ) / peso_total

        return 0.5 * (np.tanh(4.0 * impacto_bruto) + 1.0)

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
        *,
        scores_ajuda: np.ndarray | None = None,
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
        referencia_ajuda = scores if scores_ajuda is None else scores_ajuda
        validos = (
            (scores > 0)
            & (referencia_ajuda > 0)
            & ~np.isnan(custos_kg_ms)
            & (custos_kg_ms > 0)
        )
        indices[validos] = scores[validos] / custos_kg_ms[validos]
        return indices

    @classmethod
    def _distancias_euclidianas(
        cls,
        M: np.ndarray,
        vetor_ref: np.ndarray,
        *,
        pesos: np.ndarray | None = None,
    ) -> np.ndarray:
        """
        Distância euclidiana normalizada entre cada candidato e o
        ingrediente de referência (o que está sendo substituído).

        A normalização usa uma escala técnica mínima e o maior valor
        observado em candidatos/referência. Os pesos incorporam a função
        original e as necessidades atuais da formulação.
        """
        M_sub  = M[:, _IDX_PRIMARIOS]
        ref_sub = vetor_ref[_IDX_PRIMARIOS]
        escalas = cls._escalas_nutricionais(M, vetor_ref)
        diffs = (M_sub - ref_sub) / escalas
        pesos_validos = np.ones(len(_IDX_PRIMARIOS), dtype=float) if pesos is None else pesos
        return np.sqrt(((diffs ** 2) * pesos_validos).sum(axis=1) / pesos_validos.sum())

    @staticmethod
    def _escalas_nutricionais(
        M: np.ndarray,
        vetor_ref: np.ndarray,
    ) -> np.ndarray:
        """Retorna denominadores estáveis para normalizar PB/NDT/FDN/EE/Ca/P."""
        M_sub = M[:, _IDX_PRIMARIOS]
        ref_sub = vetor_ref[_IDX_PRIMARIOS]
        maximos = np.max(
            np.abs(np.vstack([M_sub, ref_sub.reshape(1, -1)])),
            axis=0,
        )
        return np.maximum(maximos, _ESCALAS_MINIMAS)

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
