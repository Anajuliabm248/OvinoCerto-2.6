"""Estimativa adaptativa de receitas a partir das referências publicadas.

Este módulo não resolve as restrições da formulação. Ele produz apenas uma
âncora inicial, acompanhada de confiança. O MotorAdequacao continua responsável
por soma, limites, travas e adequação nutricional.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp

import numpy as np

from formulacao.domain.nutrientes import Nutriente
from formulacao.domain.requisito import RequisitoNutriente


@dataclass(frozen=True)
class ContextoZootecnico:
    """Características que distinguem linhas NRC nutricionalmente próximas."""

    categoria: str
    fase: str
    peso_vivo_kg: float
    gmd_kg: float
    cms_kg: float


@dataclass(frozen=True)
class ReferenciaSuplemento:
    """Ponto calibrado: contexto, exigências e receita canônica em fração."""

    contexto: ContextoZootecnico
    pb: float
    ndt: float
    ca: float
    p: float
    ca_p: float
    receita: tuple[float, ...]
    codigo: str = ""
    ingredientes: tuple["IngredienteReferencia", ...] = ()


@dataclass(frozen=True)
class IngredienteReferencia:
    """Assinatura técnica de um componente da referência, sem ID do catálogo."""

    classificacao: str
    tipo: str
    participacao: float
    composicao: tuple[float, float, float, float, float, float]


@dataclass(frozen=True)
class EstimativaReceita:
    """Receita canônica estimada e confiabilidade da interpolação."""

    receita: np.ndarray
    confianca: float
    distancia_referencia: float
    dispersao_percentual: float
    exata: bool
    referencia_base: ReferenciaSuplemento | None = None
    referencias_ordenadas: tuple[ReferenciaSuplemento, ...] = ()


@dataclass(frozen=True)
class EstimativaPreferenciaAprendida:
    """Âncora prevista por relações nutricionais aprendidas das referências."""

    fracoes: np.ndarray
    confianca: float
    referencias_treinamento: int


# Ordem: milho, aveia, sorgo, melaço, soja, calcário, bicarbonato, cloreto.
REFERENCIAS_SUPLEMENTO_COMPLETO: tuple[ReferenciaSuplemento, ...] = (
    ReferenciaSuplemento(
        ContextoZootecnico("cordeiros_8_meses", "crescimento", 80.0, 0.5, 2.560),
        11.6015625000, 66.4062500000, 0.3554687500, 0.2851562500,
        1.2465753425,
        (0.7188, 0.1050, 0.0313, 0.0551, 0.0631, 0.0117, 0.0100, 0.0050),
    ),
    ReferenciaSuplemento(
        ContextoZootecnico("cordeiros_8_meses", "crescimento", 70.0, 0.4, 2.107),
        11.5804461319, 66.4451827243, 0.3512102515, 0.2800189843,
        1.2542372881,
        (0.6356, 0.2081, 0.0332, 0.0475, 0.0485, 0.0121, 0.0100, 0.0050),
    ),
    ReferenciaSuplemento(
        ContextoZootecnico("cordeiros_8_meses", "crescimento", 70.0, 0.3, 2.758),
        8.5206671501, 52.9369108049, 0.2429296592, 0.1994198695,
        1.2181818182,
        (0.9080, 0.0010, 0.0036, 0.0613, 0.0001, 0.0110, 0.0100, 0.0050),
    ),
    ReferenciaSuplemento(
        ContextoZootecnico("cordeiros_8_meses", "crescimento", 60.0, 0.4, 2.016),
        11.7559523810, 66.4682539683, 0.3621031746, 0.2876984127,
        1.2586206897,
        (0.4190, 0.4128, 0.0707, 0.0445, 0.0256, 0.0124, 0.0100, 0.0050),
    ),
    ReferenciaSuplemento(
        ContextoZootecnico("cordeiros_8_meses", "crescimento", 60.0, 0.3, 1.656),
        11.4734299517, 66.4251207729, 0.3442028986, 0.2717391304,
        1.2666666667,
        (0.7129, 0.1208, 0.0543, 0.0281, 0.0543, 0.0146, 0.0100, 0.0050),
    ),
    ReferenciaSuplemento(
        ContextoZootecnico("cordeiros_8_meses", "crescimento", 50.0, 0.4, 1.925),
        11.9480519481, 66.4935064935, 0.3740259740, 0.2961038961,
        1.2631578947,
        (0.7039, 0.1045, 0.0568, 0.0364, 0.0694, 0.0140, 0.0100, 0.0050),
    ),
    ReferenciaSuplemento(
        ContextoZootecnico("cordeiros_8_meses", "crescimento", 50.0, 0.3, 1.565),
        11.6932907348, 66.4536741214, 0.3578274760, 0.2811501597,
        1.2727272727,
        (0.6714, 0.1597, 0.0767, 0.0100, 0.0519, 0.0153, 0.0100, 0.0050),
    ),
    ReferenciaSuplemento(
        ContextoZootecnico("cordeiros_4_meses", "crescimento", 60.0, 0.4, 2.082),
        12.1998078770, 52.8338136407, 0.3746397695, 0.2833813641,
        1.3220338983,
        (0.3418, 0.3045, 0.2062, 0.0700, 0.0519, 0.0106, 0.0100, 0.0050),
    ),
    ReferenciaSuplemento(
        ContextoZootecnico("cordeiros_4_meses", "crescimento", 40.0, 0.4, 1.164),
        18.2989690722, 60.1374570447, 0.6013745704, 0.4381443299,
        1.3725490196,
        (0.2287, 0.2304, 0.2287, 0.0700, 0.2152, 0.0120, 0.0100, 0.0050),
    ),
    ReferenciaSuplemento(
        ContextoZootecnico("cordeiros_4_meses", "crescimento", 30.0, 0.3, 0.879),
        18.4300341297, 65.9840728100, 0.6029579067, 0.4323094425,
        1.3947368421,
        (0.2287, 0.2260, 0.2287, 0.0700, 0.2191, 0.0125, 0.0100, 0.0050),
    ),
    ReferenciaSuplemento(
        ContextoZootecnico("cordeiros_4_meses", "crescimento", 20.0, 0.3, 0.608),
        24.3421052632, 78.9473684211, 0.8388157895, 0.5756578947,
        1.4571428571,
        (0.3711, 0.0778, 0.0822, 0.0500, 0.3875, 0.0164, 0.0100, 0.0050),
    ),
    ReferenciaSuplemento(
        ContextoZootecnico("cordeiros_4_meses", "crescimento", 20.0, 0.2, 0.594),
        18.6868686869, 65.6565656566, 0.6228956229, 0.4208754209,
        1.4800000000,
        (0.3070, 0.2267, 0.1616, 0.0500, 0.2245, 0.0152, 0.0100, 0.0050),
    ),
)


class EstimadorReceitaReferencia:
    """Interpolador local conservador, com confiança e incerteza explícitas."""

    ESCALAS_CONTEXTO = np.array([20.0, 0.10, 0.50], dtype=float)
    ESCALAS_EXIGENCIAS = np.array([3.0, 8.0, 0.15, 0.12, 0.15], dtype=float)
    PESO_CONTEXTO = 0.65
    VIZINHOS = 3
    DISPERSAO_ESCALA_PERCENTUAL = 8.0
    # A amostra atual ainda é pequena e contém receitas bastante diferentes
    # em pontos zootécnicos próximos. Até haver mais validações independentes,
    # uma interpolação nunca deve se apresentar como alta confiança.
    CONFIANCA_MAXIMA_INTERPOLACAO = 0.49
    # As tabelas publicadas exibem exigências arredondadas, enquanto o NRC no
    # banco conserva a precisão de cálculo. Igualdade binária entre floats
    # faria o mesmo cenário zootécnico parecer apenas "parecido".
    TOLERANCIAS_EXATAS_CONTEXTO = np.array([0.01, 0.001, 0.001], dtype=float)
    TOLERANCIAS_EXATAS_EXIGENCIAS = np.array(
        [0.02, 0.02, 0.01, 0.01, 0.02], dtype=float
    )

    @classmethod
    def estimar(
        cls,
        contexto: ContextoZootecnico,
        requisitos: dict[Nutriente, RequisitoNutriente],
        referencias: tuple[ReferenciaSuplemento, ...] = REFERENCIAS_SUPLEMENTO_COMPLETO,
    ) -> EstimativaReceita | None:
        candidatos = [
            referencia
            for referencia in referencias
            if referencia.contexto.categoria == contexto.categoria
            and referencia.contexto.fase == contexto.fase
        ]
        vetor_exigencias = cls._vetor_exigencias(requisitos)
        if not candidatos or vetor_exigencias is None:
            return None

        distancias = np.array([
            cls._distancia(contexto, vetor_exigencias, referencia)
            for referencia in candidatos
        ])
        ordem = np.argsort(distancias)
        mais_proxima = float(distancias[ordem[0]])

        if cls._corresponde_cenario_validado(
            contexto=contexto,
            vetor_exigencias=vetor_exigencias,
            referencia=candidatos[int(ordem[0])],
        ):
            referencia = candidatos[int(ordem[0])]
            return EstimativaReceita(
                receita=np.asarray(referencia.receita, dtype=float),
                confianca=1.0,
                distancia_referencia=0.0,
                dispersao_percentual=0.0,
                exata=True,
                referencia_base=referencia,
                referencias_ordenadas=tuple(candidatos[int(i)] for i in ordem),
            )

        indices = ordem[:min(cls.VIZINHOS, len(ordem))]
        distancias_vizinhos = distancias[indices]
        pesos = 1.0 / np.square(distancias_vizinhos + 0.05)
        pesos /= float(pesos.sum())
        receitas_vizinhas = [candidatos[int(indice)].receita for indice in indices]
        # Referências persistidas podem ter conjuntos de ingredientes diferentes.
        # Nesse caso não existe vetor posicional que possa ser interpolado com
        # honestidade; a referência mais próxima ainda pode servir de guia
        # fraco, e o motor fará o mapeamento por composição/tipo.
        if len({len(receita) for receita in receitas_vizinhas}) == 1:
            receitas = np.asarray(receitas_vizinhas, dtype=float)
            receita = pesos @ receitas
            variancia = pesos @ np.square(receitas - receita)
            dispersao_percentual = float(np.sqrt(np.mean(variancia)) * 100.0)
        else:
            receita = np.asarray(candidatos[int(ordem[0])].receita, dtype=float)
            dispersao_percentual = cls.DISPERSAO_ESCALA_PERCENTUAL

        confianca_proximidade = exp(-mais_proxima)
        confianca_consistencia = exp(
            -dispersao_percentual / cls.DISPERSAO_ESCALA_PERCENTUAL
        )
        confianca_dominio = cls._confianca_dominio(contexto, candidatos)
        confianca = float(np.clip(
            confianca_proximidade * confianca_consistencia * confianca_dominio,
            0.0,
            cls.CONFIANCA_MAXIMA_INTERPOLACAO,
        ))
        return EstimativaReceita(
            receita=receita,
            confianca=confianca,
            distancia_referencia=mais_proxima,
            dispersao_percentual=dispersao_percentual,
            exata=False,
            referencia_base=candidatos[int(ordem[0])],
            referencias_ordenadas=tuple(candidatos[int(i)] for i in ordem),
        )

    @classmethod
    def _distancia(
        cls,
        contexto: ContextoZootecnico,
        vetor_exigencias: np.ndarray,
        referencia: ReferenciaSuplemento,
    ) -> float:
        observado_contexto = np.array([
            contexto.peso_vivo_kg,
            contexto.gmd_kg,
            contexto.cms_kg,
        ])
        referencia_contexto = np.array([
            referencia.contexto.peso_vivo_kg,
            referencia.contexto.gmd_kg,
            referencia.contexto.cms_kg,
        ])
        distancia_contexto = float(np.mean(np.square(
            (observado_contexto - referencia_contexto) / cls.ESCALAS_CONTEXTO
        )))
        referencia_exigencias = np.array([
            referencia.pb,
            referencia.ndt,
            referencia.ca,
            referencia.p,
            referencia.ca_p,
        ])
        distancia_exigencias = float(np.mean(np.square(
            (vetor_exigencias - referencia_exigencias) / cls.ESCALAS_EXIGENCIAS
        )))
        return float(np.sqrt(
            cls.PESO_CONTEXTO * distancia_contexto
            + (1.0 - cls.PESO_CONTEXTO) * distancia_exigencias
        ))

    @classmethod
    def _corresponde_cenario_validado(
        cls,
        contexto: ContextoZootecnico,
        vetor_exigencias: np.ndarray,
        referencia: ReferenciaSuplemento,
    ) -> bool:
        """Reconhece o mesmo cenário após o arredondamento editorial da fonte."""
        valores_contexto = np.array([
            contexto.peso_vivo_kg,
            contexto.gmd_kg,
            contexto.cms_kg,
        ])
        contexto_referencia = np.array([
            referencia.contexto.peso_vivo_kg,
            referencia.contexto.gmd_kg,
            referencia.contexto.cms_kg,
        ])
        exigencias_referencia = np.array([
            referencia.pb,
            referencia.ndt,
            referencia.ca,
            referencia.p,
            referencia.ca_p,
        ])
        return bool(
            np.all(np.abs(valores_contexto - contexto_referencia)
                   <= cls.TOLERANCIAS_EXATAS_CONTEXTO)
            and np.all(np.abs(vetor_exigencias - exigencias_referencia)
                       <= cls.TOLERANCIAS_EXATAS_EXIGENCIAS)
        )

    @classmethod
    def _confianca_dominio(
        cls,
        contexto: ContextoZootecnico,
        referencias: list[ReferenciaSuplemento],
    ) -> float:
        valores = np.array([
            [
                referencia.contexto.peso_vivo_kg,
                referencia.contexto.gmd_kg,
                referencia.contexto.cms_kg,
            ]
            for referencia in referencias
        ])
        observado = np.array([
            contexto.peso_vivo_kg,
            contexto.gmd_kg,
            contexto.cms_kg,
        ])
        abaixo = np.maximum(valores.min(axis=0) - observado, 0.0)
        acima = np.maximum(observado - valores.max(axis=0), 0.0)
        extrapolacao = float(np.linalg.norm((abaixo + acima) / cls.ESCALAS_CONTEXTO))
        return exp(-extrapolacao)

    @staticmethod
    def _vetor_exigencias(
        requisitos: dict[Nutriente, RequisitoNutriente],
    ) -> np.ndarray | None:
        valores = []
        for nutriente in (
            Nutriente.PB,
            Nutriente.NDT,
            Nutriente.CA,
            Nutriente.P,
            Nutriente.CA_P,
        ):
            requisito = requisitos.get(nutriente)
            if requisito is None:
                return None
            if requisito.alterado_pelo_usuario:
                candidatos = [
                    valor
                    for valor in (requisito.valor_min, requisito.valor_max)
                    if valor is not None
                ]
                if not candidatos:
                    return None
                valores.append(float(sum(candidatos) / len(candidatos)))
            elif requisito.valor_origem_nrc is not None:
                valores.append(float(requisito.valor_origem_nrc))
            elif requisito.valor_min is not None:
                valores.append(float(requisito.valor_min))
            elif requisito.valor_max is not None:
                valores.append(float(requisito.valor_max))
            else:
                return None
        return np.asarray(valores, dtype=float)


class EstimadorPreferenciaAprendida:
    """Aprende preferências funcionais sem guardar receitas por ingrediente.

    Usa regressão local ponderada: cada componente publicado vota conforme a
    proximidade do cenário e da assinatura bromatológica. Assim, uma fonte
    energética substituta pode receber uma estimativa mesmo que nunca tenha
    aparecido no livro.
    A saída continua sendo apenas uma âncora: limites, operadores e custo são
    decididos exclusivamente pelo MotorAdequacao.
    """

    POTENCIA_SIMILARIDADE_COMPOSICAO = 2.0
    MINIMO_REFERENCIAS = 8
    CONFIANCA_MAXIMA = 0.49

    @classmethod
    def estimar(
        cls,
        contexto: ContextoZootecnico,
        requisitos: dict[Nutriente, RequisitoNutriente],
        matriz_M: np.ndarray,
        classificacoes: tuple[str, ...],
        tipos: tuple[str, ...],
        limites_max: tuple[float, ...],
        referencias: tuple[ReferenciaSuplemento, ...],
        confianca_contextual: float,
    ) -> EstimativaPreferenciaAprendida | None:
        """Prevê uma distribuição por assinatura nutricional, nunca por ID."""
        vetor_exigencias = EstimadorReceitaReferencia._vetor_exigencias(requisitos)
        if vetor_exigencias is None or len(matriz_M) != len(tipos):
            return None
        treino = tuple(
            referencia for referencia in referencias
            if (
                referencia.contexto.categoria == contexto.categoria
                and referencia.contexto.fase == contexto.fase
                and referencia.ingredientes
            )
        )
        if len(treino) < cls.MINIMO_REFERENCIAS:
            return None

        previsoes = np.zeros(len(tipos), dtype=float)
        indices_nao_aditivos = [
            indice for indice, tipo in enumerate(tipos) if tipo != "ADITIVOS"
        ]
        for indice in indices_nao_aditivos:
            composicao = cls._composicao_ingrediente(matriz_M[indice])
            pesos: list[float] = []
            participacoes: list[float] = []
            for referencia in treino:
                distancia_cenario = EstimadorReceitaReferencia._distancia(
                    contexto, vetor_exigencias, referencia
                )
                proximidade_cenario = exp(-distancia_cenario)
                for componente in referencia.ingredientes:
                    if (
                        componente.tipo != tipos[indice]
                        or componente.classificacao != classificacoes[indice]
                    ):
                        continue
                    similaridade = cls._similaridade_composicao(
                        composicao, componente.composicao
                    )
                    pesos.append(
                        proximidade_cenario
                        * similaridade ** cls.POTENCIA_SIMILARIDADE_COMPOSICAO
                    )
                    participacoes.append(componente.participacao)
            if pesos:
                previsoes[indice] = float(np.average(participacoes, weights=pesos))

        if float(previsoes.sum()) <= 1e-12:
            return None
        fracoes = cls._normalizar_com_aditivos(
            previsoes=previsoes,
            tipos=tipos,
            limites_max=limites_max,
            treino=treino,
        )
        suporte = min(1.0, len(treino) / 20.0)
        confianca = float(np.clip(
            confianca_contextual * suporte,
            0.0,
            cls.CONFIANCA_MAXIMA,
        ))
        return EstimativaPreferenciaAprendida(
            fracoes=fracoes,
            confianca=confianca,
            referencias_treinamento=len(treino),
        )

    @classmethod
    def _normalizar_com_aditivos(
        cls,
        previsoes: np.ndarray,
        tipos: tuple[str, ...],
        limites_max: tuple[float, ...],
        treino: tuple[ReferenciaSuplemento, ...],
    ) -> np.ndarray:
        resultado = previsoes.copy()
        indices_aditivos = [i for i, tipo in enumerate(tipos) if tipo == "ADITIVOS"]
        indices_nao_aditivos = [i for i, tipo in enumerate(tipos) if tipo != "ADITIVOS"]
        if not indices_aditivos:
            resultado /= float(resultado.sum())
            return resultado

        massas_aditivos = [
            sum(item.participacao for item in referencia.ingredientes if item.tipo == "ADITIVOS")
            for referencia in treino
        ]
        massa_aditivos = min(
            float(np.median(massas_aditivos)),
            float(sum(max(0.0, limites_max[i]) for i in indices_aditivos)),
        )
        massa_aditivos = float(np.clip(massa_aditivos, 0.0, 0.10))
        resultado[indices_nao_aditivos] *= (1.0 - massa_aditivos) / float(
            resultado[indices_nao_aditivos].sum()
        )
        pesos_aditivos = np.array([
            max(limites_max[i], 1e-9) for i in indices_aditivos
        ])
        resultado[indices_aditivos] = massa_aditivos * pesos_aditivos / float(pesos_aditivos.sum())
        return resultado

    @staticmethod
    def _composicao_ingrediente(matriz_linha: np.ndarray) -> np.ndarray:
        return np.asarray(matriz_linha[:6], dtype=float)

    @staticmethod
    def _similaridade_composicao(
        observada: np.ndarray,
        referencia: tuple[float, float, float, float, float, float],
    ) -> float:
        esperada = np.asarray(referencia, dtype=float)
        escalas = np.maximum(
            np.abs(esperada) * 0.25,
            np.array([2.0, 5.0, 5.0, 1.0, 0.20, 0.10]),
        )
        distancia = float(np.sqrt(np.mean(np.square(
            (observada - esperada) / escalas
        ))))
        return float(np.exp(-distancia))
