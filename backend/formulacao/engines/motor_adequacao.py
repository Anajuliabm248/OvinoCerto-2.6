"""

Resolve os problemas de geração inicial e redistribuição de participações
usando scipy.optimize.minimize (SLSQP).

  1. gerar_distribuicao_inicial(): dado um conjunto de ingredientes
     e requisitos nutricionais, encontra um vetor de participações
     x que soma 1 e tenta satisfazer todos os requisitos.

  2. redistribuir(): dado que alguns ingredientes estão travados
     (MANUAL_TRAVADA), redistribui as participações dos livres
     (CALCULADA) no espaço restante (1 - Σ travados).

As regras estruturais são rígidas: soma, ingredientes travados, limites de
participação e percentual de volumoso. Os requisitos nutricionais entram como
penalidade de melhor esforço; quando a seleção não permite atendê-los, o motor
preserva uma distribuição válida e o MotorAlertas informa os desvios.

Em dietas mistas (volumoso + concentrado), o piso padrão de PB é uma exceção:
ele é aplicado como restrição quando for viável junto às regras estruturais.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import exp

import numpy as np
from scipy.optimize import Bounds, linprog, minimize

from formulacao.domain.nutrientes import NUTRIENTES_ORDEM, Nutriente, indice_de
from formulacao.domain.participacao import ParticipacaoVetor
from formulacao.domain.requisito import RequisitoNutriente
from formulacao.engines.estimador_referencia import (
    ContextoZootecnico,
    EstimadorPreferenciaAprendida,
    EstimadorReceitaReferencia,
    ReferenciaSuplemento,
)



# Tipos de entrada/saída

@dataclass(frozen=True)
class ConfiguracaoIngrediente:
    """
    Metadados por ingrediente que o MotorAdequacao precisa conhecer.
    Desacoplado do ORM: o Application Service popula esta dataclass
    a partir do model Ingrediente antes de chamar o motor.
    """
    classificacao: str          # "VOLUMOSO" | "CONCENTRADO"
    limite_min: float = 0.0     # fração mínima de inclusão (0-1)
    limite_max: float = 1.0     # fração máxima de inclusão (0-1)
    tipo: str = "OUTRO"         # ENERGETICO | PROTEICO | MINERAL | ADITIVOS | ...
    custo_por_kg_ms: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "classificacao", self.classificacao.upper())
        object.__setattr__(self, "tipo", self.tipo.upper())
        if not (0.0 <= self.limite_min <= self.limite_max <= 1.0):
            raise ValueError(
                f"ConfiguracaoIngrediente: limites inválidos "
                f"[{self.limite_min}, {self.limite_max}]"
            )
        if self.custo_por_kg_ms is not None and self.custo_por_kg_ms < 0.0:
            raise ValueError("ConfiguracaoIngrediente: custo por kg de MS inválido")


class PerfilNutricional(str, Enum):
    """Define se os requisitos descrevem uma dieta ou só um suplemento."""

    DIETA_TOTAL = "DIETA_TOTAL"
    SUPLEMENTO_CONCENTRADO = "SUPLEMENTO_CONCENTRADO"


class ObjetivoGeracao(str, Enum):
    """Critério usado depois de respeitar todas as restrições."""

    EQUILIBRADO = "EQUILIBRADO"
    MENOR_CUSTO = "MENOR_CUSTO"


@dataclass(frozen=True)
class ResultadoDistribuicao:
    """
    Resultado do MotorAdequacao.

    fracoes    : vetor de participações em 0-1, indexado da mesma
                 forma que os inputs.
    convergiu  : True se o SLSQP convergiu dentro das tolerâncias.
                 False indica fallback numérico; as regras estruturais
                 continuam válidas e os alertas reportam desvios nutricionais.
    mensagem   : descrição do status do solver para log/auditoria.
    """
    fracoes: np.ndarray = field(repr=False)
    convergiu: bool
    mensagem: str
    origem_alvo: str = "heuristica"
    confianca_alvo: float | None = None


# Motor

class MotorAdequacao:
    """Encontra participações válidas sem romper soma, travas, classes e limites."""

    # Percentual-alvo de volumosos na distribuição heurística inicial.
    PERCENTUAL_ALVO_VOLUMOSO: float = 0.50

    # Tolerância do SLSQP
    SLSQP_FTOL: float = 1e-9
    SLSQP_MAXITER: int = 1000

    # Evita que ingredientes escolhidos desapareçam da geração inicial.
    # O valor é reduzido automaticamente quando o orçamento da classe é menor.
    MINIMO_TECNICO_GERACAO: float = 0.001

    # Equilibra adequação nutricional e estabilidade da distribuição. As metas
    # nutricionais orientam o resultado, mas não podem romper regras rígidas.
    PESO_ADEQUACAO_NUTRICIONAL: float = 1.0

    PESOS_HEURISTICOS_TIPO: dict[str, float] = {
        "ENERGETICO": 1.0,
        "PROTEICO": 0.25,
        "MINERAL": 0.025,
        "ADITIVOS": 0.01,
        "OUTRO": 0.50,
    }

    # Perfil usado quando todos os itens selecionados são concentrados. O
    # manual de referência trata essas misturas como suplementos, não como
    # dietas completas: PB e NDT orientam a formulação, enquanto FDN continua
    # sendo reportada por alerta sem puxar artificialmente a distribuição.
    ORCAMENTOS_SUPLEMENTO_TIPO: dict[str, float] = {
        "ENERGETICO": 0.68,
        "PROTEICO": 0.30,
        "MINERAL": 0.02,
        "ADITIVOS": 0.01,
        "OUTRO": 0.25,
    }
    FDN_LIMIAR_ENERGETICO_SUPLEMENTO: float = 30.0
    EXPOENTE_PENALIDADE_FIBRA_ENERGETICO: float = 4.0
    ESCALA_NDT_PESO_ENERGETICO: float = 8.0
    ALVO_CA_P_SUPLEMENTO: float = 2.05
    PESO_CA_P_SUPLEMENTO: float = 1.0
    PESO_NDT_ALVO_SUPLEMENTO: float = 100.0
    PESO_DENSIDADE_ENERGETICA_SUPLEMENTO: float = 0.20
    LIMIAR_NDT_RELATIVO_PARA_ALVO: float = 0.85

    # Formulações concentradas publicadas no manual. Cada perfil contém:
    # (PB NRC, NDT NRC, receita com trigo/milho, receita com milho/aveia).
    # As receitas são indexadas por função nutricional, não por ID/nome:
    # - trigo/milho: energético de maior FDN, energético de menor FDN,
    #   proteico e mineral;
    # - milho/aveia: energético de maior NDT, energético de menor NDT,
    #   proteico e mineral.
    PERFIS_REFERENCIA_SUPLEMENTO: tuple[
        tuple[float, float, tuple[float, ...], tuple[float, ...]], ...
    ] = (
        (18.6868686869, 65.6565656566,
         (0.0912, 0.6626, 0.2276, 0.0186),
         (0.4027, 0.3847, 0.1960, 0.0166)),
        (24.3421052632, 78.9473684211,
         (0.2013, 0.4268, 0.3488, 0.0231),
         (0.3436, 0.2822, 0.3528, 0.0214)),
        (12.4406457740, 53.1813865147,
         (0.1938, 0.7366, 0.0497, 0.0199),
         (0.4795, 0.4807, 0.0255, 0.0143)),
        (14.0200000000, 79.1400000000,
         (0.2704, 0.6327, 0.0746, 0.0223),
         (0.4920, 0.4183, 0.0738, 0.0159)),
    )

    # Receitas do manual para o conjunto completo milho/aveia/sorgo/melaço,
    # soja, calcário, bicarbonato e cloreto. A ordem das participações é a de
    # ASSINATURAS_PERFIL_COMPLETO, seguida pelos dois aditivos. PB e NDT são
    # os valores NRC usados para identificar o cenário, não a composição
    # calculada da receita.
    ASSINATURAS_PERFIL_COMPLETO: tuple[str, ...] = (
        "MILHO",
        "AVEIA",
        "SORGO",
        "MELACO",
        "SOJA",
        "CALCARIO",
    )
    # Referências publicadas pertencem à suíte de calibração; não são usadas
    # como destino da geração em produção.
    PERFIS_REFERENCIA_SUPLEMENTO_COMPLETO: tuple[tuple, ...] = ()
    TOLERANCIA_PB_PERFIL_REFERENCIA: float = 0.75
    TOLERANCIA_NDT_PERFIL_REFERENCIA: float = 1.0
    RTOL_ASSINATURA_INGREDIENTE: float = 0.03
    ATOL_ASSINATURA_INGREDIENTE: float = 0.25
    ASSINATURAS_INGREDIENTES_REFERENCIA: dict[str, tuple[float, ...]] = {
        "TRIGO": (17.12, 71.35, 43.96, 3.58, 0.19, 0.95),
        "MILHO": (9.10, 86.03, 14.39, 4.18, 0.03, 0.25),
        "AVEIA": (14.21, 75.24, 27.69, 5.13, 0.13, 0.35),
        "SORGO": (9.70, 78.80, 17.27, 2.96, 0.04, 0.28),
        "MELACO": (3.30, 69.75, 6.03, 1.36, 1.70, 0.12),
        "SOJA": (48.76, 80.73, 15.37, 1.75, 0.33, 0.57),
        "CALCARIO": (0.0, 0.0, 0.0, 0.0, 37.35, 0.01),
    }
    CONFIANCA_MINIMA_ESTIMADOR: float = 0.20
    CONFIANCA_ALTA_ESTIMADOR: float = 0.80

    
    # API pública
    

    @classmethod
    def gerar_distribuicao_inicial(
        cls,
        matriz_M: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
        configuracoes: list[ConfiguracaoIngrediente],
        percentual_alvo_volumoso: float | None = None,
        contexto_zootecnico: ContextoZootecnico | None = None,
        objetivo: ObjetivoGeracao | str = ObjetivoGeracao.EQUILIBRADO,
        referencias_suplemento: tuple[ReferenciaSuplemento, ...] = (),
    ) -> ResultadoDistribuicao:
        """
        Gera a distribuição inicial de %MS para todos os ingredientes.

        matriz_M       : shape (n, N_NUTRIENTES), valores em % da MS.
        configuracoes  : uma ConfiguracaoIngrediente por ingrediente,
                         na mesma ordem de matriz_M.
        """
        n = len(configuracoes)
        if n == 0:
            return ResultadoDistribuicao(
                fracoes=np.array([], dtype=float),
                convergiu=True,
                mensagem="Nenhum ingrediente.",
            )
        cls._validar_dimensoes(matriz_M, n)
        objetivo_normalizado = cls._normalizar_objetivo(objetivo)

        alvo_vol = cls._normalizar_percentual_volumoso(
            percentual_alvo_volumoso
            if percentual_alvo_volumoso is not None
            else cls.PERCENTUAL_ALVO_VOLUMOSO
        )

        mascara_volumoso = cls._mascara_volumoso(configuracoes)
        perfil_nutricional = cls._perfil_nutricional(configuracoes)
        (
            x_alvo,
            usa_perfil_referencia,
            origem_alvo,
            confianca_alvo,
        ) = cls._preparar_x_alvo(
            configuracoes=configuracoes,
            percentual_volumoso=alvo_vol,
            matriz_M=matriz_M,
            requisitos=requisitos,
            contexto_zootecnico=contexto_zootecnico,
            referencias_suplemento=referencias_suplemento,
        )
        bounds = cls._bounds_geracao(
            configuracoes=configuracoes,
            soma_total=1.0,
            percentual_volumoso=alvo_vol,
            aplicar_piso_tecnico=not usa_perfil_referencia,
        )
        return cls._resolver(
            n=n,
            matriz_M_sub=matriz_M,
            requisitos=requisitos,
            x_alvo_sub=x_alvo,
            bounds_sub=bounds,
            soma_alvo=1.0,
            contrib_fixas=np.zeros(len(NUTRIENTES_ORDEM)),
            mascara_volumoso_sub=mascara_volumoso,
            soma_volumoso_alvo=alvo_vol,
            modo_suplemento_concentrado=(
                perfil_nutricional == PerfilNutricional.SUPLEMENTO_CONCENTRADO
            ),
            dieta_mista=cls._tem_volumoso_e_concentrado(configuracoes),
            usar_perfil_referencia=usa_perfil_referencia,
            origem_alvo=origem_alvo,
            confianca_alvo=confianca_alvo,
            custos_sub=cls._custos_configuracoes(configuracoes),
            objetivo=objetivo_normalizado,
        )

    @classmethod
    def redistribuir(
        cls,
        matriz_M: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
        participacao_atual: ParticipacaoVetor,
        configuracoes: list[ConfiguracaoIngrediente],
        percentual_alvo_volumoso: float | None = None,
        reiniciar_livres: bool = False,
        contexto_zootecnico: ContextoZootecnico | None = None,
        objetivo: ObjetivoGeracao | str = ObjetivoGeracao.EQUILIBRADO,
        referencias_suplemento: tuple[ReferenciaSuplemento, ...] = (),
    ) -> ResultadoDistribuicao:
        """
        Redistribui participações dos ingredientes CALCULADA quando
        há ingredientes MANUAL_TRAVADA.

        Retorna um novo vetor de participações COMPLETO (travados
        permanecem com seus valores atuais; livres são recalculados).

        Se espaco_livre <= 0 (travados já somam >= 100%), retorna
        resultado não-convergido — MotorAlertas emitirá alerta.
        """
        n = len(participacao_atual)
        if len(configuracoes) != n:
            raise ValueError(
                "A quantidade de configurações deve corresponder à quantidade "
                "de ingredientes da participação."
            )
        cls._validar_dimensoes(matriz_M, n)
        objetivo_normalizado = cls._normalizar_objetivo(objetivo)

        mascara_travados = participacao_atual.mascara_travados()
        mascara_livres   = participacao_atual.mascara_livres()
        indices_livres = np.where(mascara_livres)[0]
        n_livres = len(indices_livres)

        espaco_livre = participacao_atual.espaco_livre()
        if espaco_livre < -1e-9:
            raise ValueError(
                f"Redistribuição inviável: as participações travadas somam "
                f"{participacao_atual.soma_travados() * 100:.2f}%, acima de 100%."
            )

        if n_livres == 0:
            if abs(espaco_livre) > 1e-9:
                raise ValueError(
                    "Redistribuição inviável: todos os ingredientes estão "
                    "travados e a soma não fecha em 100%."
                )
            return ResultadoDistribuicao(
                fracoes=participacao_atual.fracoes.copy(),
                convergiu=True,
                mensagem="Nenhum ingrediente livre para redistribuir.",
            )

        if espaco_livre <= 1e-9:
            raise ValueError(
                "Redistribuição inviável: não há espaço para os ingredientes "
                "livres. Reduza ou destrave uma participação manual."
            )

        # Caso trivial: único ingrediente livre. Ainda assim, os limites são
        # rígidos; uma sobra acima do máximo deve rejeitar a operação.
        if n_livres == 1:
            idx_livre = int(indices_livres[0])
            cfg_livre = configuracoes[idx_livre]
            cls._projetar_soma(
                np.array([espaco_livre], dtype=float),
                espaco_livre,
                [(cfg_livre.limite_min, cfg_livre.limite_max)],
            )
            fracoes_resultado = participacao_atual.fracoes.copy()
            fracoes_resultado[idx_livre] = espaco_livre
            return ResultadoDistribuicao(
                fracoes=fracoes_resultado,
                convergiu=True,
                mensagem="Redistribuição trivial (único ingrediente livre).",
            )

        # Sub-matrizes apenas para os livres
        M_livres    = matriz_M[indices_livres, :]
        cfg_livres  = [configuracoes[i] for i in indices_livres]

        # Contribuição nutricional fixa dos travados
        fracoes_travados = participacao_atual.fracoes[mascara_travados]
        M_travados       = matriz_M[mascara_travados, :]
        # contrib em % da MS total: (fracao_trav * valor_nutriente_pct)
        contrib_fixas = fracoes_travados @ M_travados  # shape (N_NUTRIENTES,)

        # x_alvo para os livres: distribuição proporcional anterior
        # escalada para o novo espaço livre (princípio de menor mudança)
        fracoes_livres_atuais = participacao_atual.fracoes[indices_livres]
        soma_livres_atual = fracoes_livres_atuais.sum()
        alvo_vol = cls._normalizar_percentual_volumoso(
            percentual_alvo_volumoso
            if percentual_alvo_volumoso is not None
            else cls.PERCENTUAL_ALVO_VOLUMOSO
        )

        soma_volumoso_alvo = None
        percentual_volumoso_livre = alvo_vol
        if percentual_alvo_volumoso is not None:
            mascara_volumoso_total = cls._mascara_volumoso(configuracoes)
            volumoso_travado = float(
                participacao_atual.fracoes[mascara_travados & mascara_volumoso_total].sum()
            )
            soma_volumoso_alvo = alvo_vol - volumoso_travado
            if (
                soma_volumoso_alvo < -1e-9
                or soma_volumoso_alvo > espaco_livre + 1e-9
            ):
                raise ValueError(
                    "Alvo de volumoso inviável: os ingredientes travados já "
                    "ocupam uma participação incompatível com o alvo informado."
                )
            soma_volumoso_alvo = min(
                espaco_livre,
                max(0.0, soma_volumoso_alvo),
            )
            percentual_volumoso_livre = soma_volumoso_alvo / espaco_livre

        usar_perfil_referencia = False
        origem_alvo = "distribuicao_atual"
        confianca_alvo = None
        if reiniciar_livres:
            (
                x_alvo_livres,
                usar_perfil_referencia,
                origem_alvo,
                confianca_alvo,
            ) = cls._preparar_x_alvo(
                configuracoes=cfg_livres,
                percentual_volumoso=percentual_volumoso_livre,
                matriz_M=M_livres,
                requisitos=requisitos,
                permitir_perfil_referencia=not bool(np.any(mascara_travados)),
                contexto_zootecnico=contexto_zootecnico,
                referencias_suplemento=referencias_suplemento,
            )
            x_alvo_livres = x_alvo_livres * espaco_livre
        elif soma_livres_atual > 1e-9:
            x_alvo_livres = fracoes_livres_atuais / soma_livres_atual * espaco_livre
        else:
            x_alvo_livres = cls._x_alvo_heuristico(
                cfg_livres,
                alvo_vol,
                matriz_M=M_livres,
            )
            x_alvo_livres = x_alvo_livres * espaco_livre

        bounds_geracao = None
        if reiniciar_livres:
            bounds_geracao = cls._bounds_geracao(
                configuracoes=cfg_livres,
                soma_total=espaco_livre,
                percentual_volumoso=percentual_volumoso_livre,
                aplicar_piso_tecnico=not usar_perfil_referencia,
            )

        # Os limites cadastrados são rígidos. A menor mudança possível fica
        # no objetivo do solver; não vira bound porque isso poderia impedir
        # o fechamento em 100% depois de um travamento manual amplo.
        bounds_livres = []
        for i, idx_global in enumerate(indices_livres):
            cfg = configuracoes[idx_global]
            fracao_atual = participacao_atual.fracoes[idx_global]
            if reiniciar_livres:
                lo, hi = bounds_geracao[i]
                hi = min(hi, espaco_livre)
            else:
                lo = cfg.limite_min
                hi = min(cfg.limite_max, espaco_livre)
                if fracao_atual <= 1e-12 and hi > 0.0:
                    lo = max(
                        lo,
                        min(
                            cls.MINIMO_TECNICO_GERACAO,
                            espaco_livre / (2.0 * n_livres),
                            hi,
                        ),
                    )
            if lo > hi + 1e-12:
                raise ValueError(
                    "Redistribuição inviável: o limite mínimo de um ingrediente "
                    "é maior que o espaço disponível."
                )
            bounds_livres.append((lo, hi))

        mascara_volumoso_livres = cls._mascara_volumoso(cfg_livres)

        resultado_livres = cls._resolver(
            n=n_livres,
            matriz_M_sub=M_livres,
            requisitos=requisitos,
            x_alvo_sub=x_alvo_livres,
            bounds_sub=bounds_livres,
            soma_alvo=espaco_livre,
            contrib_fixas=contrib_fixas,
            mascara_volumoso_sub=mascara_volumoso_livres,
            soma_volumoso_alvo=soma_volumoso_alvo,
            modo_suplemento_concentrado=(
                cls._perfil_nutricional(configuracoes)
                == PerfilNutricional.SUPLEMENTO_CONCENTRADO
            ),
            dieta_mista=cls._tem_volumoso_e_concentrado(configuracoes),
            usar_perfil_referencia=usar_perfil_referencia,
            origem_alvo=origem_alvo,
            confianca_alvo=confianca_alvo,
            custos_sub=cls._custos_configuracoes(cfg_livres),
            objetivo=objetivo_normalizado,
        )

        # Recompor vetor completo
        fracoes_resultado = participacao_atual.fracoes.copy()
        fracoes_resultado[indices_livres] = resultado_livres.fracoes

        return ResultadoDistribuicao(
            fracoes=fracoes_resultado,
            convergiu=resultado_livres.convergiu,
            mensagem=resultado_livres.mensagem,
            origem_alvo=resultado_livres.origem_alvo,
            confianca_alvo=resultado_livres.confianca_alvo,
        )

    
    # Implementação interna
    

    @classmethod
    def _resolver(
        cls,
        n: int,
        matriz_M_sub: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
        x_alvo_sub: np.ndarray,
        bounds_sub: list[tuple[float, float]],
        soma_alvo: float,
        contrib_fixas: np.ndarray,
        mascara_volumoso_sub: np.ndarray | None = None,
        soma_volumoso_alvo: float | None = None,
        modo_suplemento_concentrado: bool = False,
        dieta_mista: bool = False,
        usar_perfil_referencia: bool = False,
        origem_alvo: str = "heuristica",
        confianca_alvo: float | None = None,
        custos_sub: np.ndarray | None = None,
        objetivo: ObjetivoGeracao = ObjetivoGeracao.EQUILIBRADO,
    ) -> ResultadoDistribuicao:
        """
        Núcleo do otimizador. Opera apenas sobre o subconjunto de
        ingredientes relevante (todos ou só os livres).

        contrib_fixas: contribuição nutricional já fixada pelos
        ingredientes travados (shape N_NUTRIENTES). Ajusta o RHS das
        restrições para que o solver opere apenas sobre os livres.
        """
        restricoes_suplemento: list[dict] = []
        ndt_alvo_suplemento = None
        ca_p_alvo_suplemento = None
        # Uma referência exata já foi publicada como suplemento equilibrado.
        # Não adicionamos uma igualdade artificial de PB/NDT sobre ela: os
        # operadores configurados pelo usuário continuam como restrições, mas
        # o motor não deve elevar NDT apenas por uma preferência interna.
        if modo_suplemento_concentrado and not usar_perfil_referencia:
            (
                restricoes_suplemento,
                ndt_alvo_suplemento,
                ca_p_alvo_suplemento,
            ) = cls._preparar_perfil_suplemento_concentrado(
                matriz_M_sub=matriz_M_sub,
                requisitos=requisitos,
                bounds_sub=bounds_sub,
                soma_alvo=soma_alvo,
                contrib_fixas=contrib_fixas,
                usar_perfil_referencia=usar_perfil_referencia,
            )

        def objetivo(x: np.ndarray) -> float:
            diff = x - x_alvo_sub
            desvio_distribuicao = float(diff @ diff)
            desvio_nutricional = cls._penalidade_nutricional(
                x=x,
                matriz_M_sub=matriz_M_sub,
                requisitos=requisitos,
                contrib_fixas=contrib_fixas,
                ignorar_fdn_padrao=modo_suplemento_concentrado,
                ignorar_minerais_padrao=usar_perfil_referencia,
            )
            referencia_suplemento = 0.0
            if modo_suplemento_concentrado and not usar_perfil_referencia:
                referencia_suplemento = cls._penalidade_suplemento_concentrado(
                    x=x,
                    matriz_M_sub=matriz_M_sub,
                    contrib_fixas=contrib_fixas,
                    ndt_alvo=ndt_alvo_suplemento,
                    ca_p_alvo=ca_p_alvo_suplemento,
                )
            return (
                desvio_distribuicao
                + cls.PESO_ADEQUACAO_NUTRICIONAL * desvio_nutricional
                + referencia_suplemento
                + cls._penalidade_objetivo(
                    x=x,
                    matriz_M_sub=matriz_M_sub,
                    custos_sub=custos_sub,
                    objetivo=objetivo,
                )
            )

        constraints = [
            {
                "type": "eq",
                "fun": lambda x: float(np.sum(x)) - soma_alvo,
                "jac": lambda x: np.ones(n),
            }
        ]
        alvo_volumoso_validado = None
        if soma_volumoso_alvo is not None and mascara_volumoso_sub is not None:
            alvo_viavel = cls._validar_soma_subgrupo_viavel(
                bounds_sub=bounds_sub,
                mascara=mascara_volumoso_sub,
                soma_alvo=soma_volumoso_alvo,
                soma_total_alvo=soma_alvo,
                nome="volumoso",
            )
            alvo_volumoso_validado = alvo_viavel
            if np.any(mascara_volumoso_sub) and not np.all(mascara_volumoso_sub):
                coef_vol = mascara_volumoso_sub.astype(float)
                constraints.append({
                    "type": "eq",
                    "fun": lambda x, c=coef_vol, alvo=alvo_viavel: float(c @ x) - alvo,
                    "jac": lambda x, c=coef_vol: c,
                })

        exigir_pb_padrao = cls._pb_padrao_rigido_em_dieta_mista(
            matriz_M_sub=matriz_M_sub,
            requisitos=requisitos,
            bounds_sub=bounds_sub,
            soma_alvo=soma_alvo,
            contrib_fixas=contrib_fixas,
            mascara_volumoso_sub=mascara_volumoso_sub,
            soma_volumoso_alvo=alvo_volumoso_validado,
            dieta_mista=dieta_mista,
        )

        constraints.extend(restricoes_suplemento)
        constraints.extend(
            cls._restricoes_nutricionais_explicitas(
                matriz_M_sub=matriz_M_sub,
                requisitos=requisitos,
                contrib_fixas=contrib_fixas,
                incluir_pb_padrao=exigir_pb_padrao,
            )
        )

        bounds = Bounds(
            lb=[b[0] for b in bounds_sub],
            ub=[b[1] for b in bounds_sub],
        )

        # O ponto inicial já satisfaz todas as regras estruturais. Isso também
        # fornece um fallback válido se o otimizador numérico falhar.
        x0 = cls._projetar_estrutura(
            x=x_alvo_sub.copy(),
            soma_alvo=soma_alvo,
            bounds=bounds_sub,
            mascara_subgrupo=mascara_volumoso_sub,
            soma_subgrupo_alvo=alvo_volumoso_validado,
        )
        # Em modo equilibrado, uma referência exata que já atende aos limites
        # estruturais e aos operadores explícitos é uma solução válida por si
        # só. Evitar uma nova otimização numérica impede que tolerâncias e
        # pesos internos afastem a receita publicada. Para MENOR_CUSTO o
        # solver continua livre para procurar economia dentro das regras.
        if (
            usar_perfil_referencia
            and objetivo == ObjetivoGeracao.EQUILIBRADO
            and cls._atende_requisitos_explicitos(
                x=x0,
                matriz_M_sub=matriz_M_sub,
                requisitos=requisitos,
                contrib_fixas=contrib_fixas,
                incluir_pb_padrao=exigir_pb_padrao,
            )
        ):
            return ResultadoDistribuicao(
                fracoes=x0,
                convergiu=True,
                mensagem=(
                    "Referência validada preservada: atende soma, limites e "
                    "operadores explícitos."
                ),
                origem_alvo=origem_alvo,
                confianca_alvo=confianca_alvo,
            )
        resultado = minimize(
            objetivo,
            x0=x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": cls.SLSQP_FTOL, "maxiter": cls.SLSQP_MAXITER},
        )

        if resultado.success:
            fracoes = cls._projetar_estrutura(
                x=resultado.x,
                soma_alvo=soma_alvo,
                bounds=bounds_sub,
                mascara_subgrupo=mascara_volumoso_sub,
                soma_subgrupo_alvo=alvo_volumoso_validado,
            )
            return ResultadoDistribuicao(
                fracoes=fracoes,
                convergiu=True,
                mensagem=(
                    f"Distribuição estrutural válida gerada em {resultado.nit} "
                    "iterações; requisitos alterados explicitamente"
                    + (
                        " e o piso padrão de PB da dieta mista"
                        if exigir_pb_padrao
                        else ""
                    )
                    + " foram aplicados como restrições. "
                    f"Alvo inicial: {origem_alvo}."
                ),
                origem_alvo=origem_alvo,
                confianca_alvo=confianca_alvo,
            )

        return ResultadoDistribuicao(
            fracoes=x0,
            convergiu=False,
            mensagem=(
                f"SLSQP não convergiu ({resultado.message}). "
                "Mantida a distribuição estrutural; revise requisitos explícitos "
                "e limites de inclusão, pois podem ser inviáveis em conjunto."
            ),
            origem_alvo=origem_alvo,
            confianca_alvo=confianca_alvo,
        )

    @staticmethod
    def _penalidade_nutricional(
        x: np.ndarray,
        matriz_M_sub: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
        contrib_fixas: np.ndarray,
        ignorar_fdn_padrao: bool = False,
        ignorar_minerais_padrao: bool = False,
    ) -> float:
        penalidade = 0.0
        totais = x @ matriz_M_sub + contrib_fixas

        for nutriente, requisito in requisitos.items():
            requisito_padrao = (
                requisito.valor_origem_nrc is not None
                and not requisito.alterado_pelo_usuario
            )
            if requisito_padrao and (
                (ignorar_fdn_padrao and nutriente == Nutriente.FDN)
                or (
                    ignorar_minerais_padrao
                    and nutriente in {Nutriente.CA, Nutriente.P, Nutriente.CA_P}
                )
            ):
                continue
            lo, hi = requisito.limites_lp()

            if nutriente == Nutriente.CA_P:
                idx_ca = indice_de(Nutriente.CA)
                idx_p = indice_de(Nutriente.P)
                valor = totais[idx_ca] / totais[idx_p] if totais[idx_p] > 1e-12 else 0.0
            else:
                valor = totais[NUTRIENTES_ORDEM.index(nutriente)]

            if lo is not None and valor < lo:
                escala = max(abs(lo), 1.0)
                penalidade += ((lo - valor) / escala) ** 2
            if hi is not None and valor > hi:
                escala = max(abs(hi), 1.0)
                penalidade += ((valor - hi) / escala) ** 2

        return float(penalidade)

    @staticmethod
    def _atende_requisitos_explicitos(
        x: np.ndarray,
        matriz_M_sub: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
        contrib_fixas: np.ndarray,
        incluir_pb_padrao: bool = False,
    ) -> bool:
        """Valida escolhas explícitas e, quando aplicável, o piso padrão de PB."""
        totais = x @ matriz_M_sub + contrib_fixas
        for nutriente, requisito in requisitos.items():
            pb_padrao_rigido = (
                incluir_pb_padrao
                and nutriente == Nutriente.PB
                and MotorAdequacao._alvo_padrao_minimo(requisitos, Nutriente.PB)
                is not None
            )
            if not requisito.alterado_pelo_usuario and not pb_padrao_rigido:
                continue
            if nutriente == Nutriente.CA_P:
                ca = totais[indice_de(Nutriente.CA)]
                fosforo = totais[indice_de(Nutriente.P)]
                valor = ca / fosforo if fosforo > 1e-12 else 0.0
            else:
                valor = totais[indice_de(nutriente)]
            minimo, maximo = requisito.limites_lp()
            if minimo is not None and valor < minimo - 1e-8:
                return False
            if maximo is not None and valor > maximo + 1e-8:
                return False
        return True

    @staticmethod
    def _penalidade_objetivo(
        x: np.ndarray,
        matriz_M_sub: np.ndarray,
        custos_sub: np.ndarray | None,
        objetivo: ObjetivoGeracao,
    ) -> float:
        """Aplica somente o critério escolhido depois das restrições."""
        if objetivo == ObjetivoGeracao.MENOR_CUSTO:
            if custos_sub is None or not np.any(custos_sub > 0.0):
                return 0.0
            escala = float(np.max(custos_sub))
            return float(x @ custos_sub) / escala
        return 0.0

    @classmethod
    def _restricoes_nutricionais_explicitas(
        cls,
        matriz_M_sub: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
        contrib_fixas: np.ndarray,
        incluir_pb_padrao: bool = False,
    ) -> list[dict]:
        """Transforma operadores escolhidos pelo usuário em restrições reais.

        O NRC padrão continua sendo melhor esforço: uma seleção de ingredientes
        pode não conseguir atendê-lo. Ao editar um requisito, porém, o usuário
        espera semântica efetiva para ``=``, ``>=``, ``<=`` e ``ENTRE``.
        Em dieta mista viável, o piso padrão de PB também é rígido.
        """
        restricoes: list[dict] = []
        for nutriente, requisito in requisitos.items():
            pb_padrao_rigido = (
                incluir_pb_padrao
                and nutriente == Nutriente.PB
                and cls._alvo_padrao_minimo(requisitos, Nutriente.PB) is not None
            )
            if not requisito.alterado_pelo_usuario and not pb_padrao_rigido:
                continue

            limite_min, limite_max = requisito.limites_lp()
            if nutriente == Nutriente.CA_P:
                if limite_min is not None:
                    coeficiente, fixo = cls._coeficiente_ca_p(
                        matriz_M_sub, contrib_fixas, limite_min
                    )
                    restricoes.append({
                        "type": "ineq",
                        "fun": lambda x, c=coeficiente, f=fixo: float(c @ x) + f,
                        "jac": lambda x, c=coeficiente: c,
                    })
                if limite_max is not None:
                    coeficiente, fixo = cls._coeficiente_ca_p(
                        matriz_M_sub, contrib_fixas, limite_max
                    )
                    restricoes.append({
                        "type": "ineq",
                        "fun": lambda x, c=coeficiente, f=fixo: -float(c @ x) - f,
                        "jac": lambda x, c=coeficiente: -c,
                    })
                continue

            coeficiente, fixo = cls._coeficiente_requisito(
                matriz_M_sub, contrib_fixas, nutriente
            )
            if limite_min is not None:
                restricoes.append({
                    "type": "ineq",
                    "fun": lambda x, c=coeficiente, f=fixo, alvo=limite_min: float(c @ x) + f - alvo,
                    "jac": lambda x, c=coeficiente: c,
                })
            if limite_max is not None:
                restricoes.append({
                    "type": "ineq",
                    "fun": lambda x, c=coeficiente, f=fixo, alvo=limite_max: alvo - float(c @ x) - f,
                    "jac": lambda x, c=coeficiente: -c,
                })
        return restricoes

    @staticmethod
    def _coeficiente_requisito(
        matriz_M_sub: np.ndarray,
        contrib_fixas: np.ndarray,
        nutriente: Nutriente,
    ) -> tuple[np.ndarray, float]:
        """Converte um requisito em expressão linear sobre os ingredientes livres."""
        indice = indice_de(nutriente)
        return matriz_M_sub[:, indice], float(contrib_fixas[indice])

    @staticmethod
    def _coeficiente_ca_p(
        matriz_M_sub: np.ndarray,
        contrib_fixas: np.ndarray,
        alvo: float,
    ) -> tuple[np.ndarray, float]:
        # Ca/P >= r é equivalente a Ca - r*P >= 0. A mesma expressão serve
        # para o limite superior, alterando apenas o sentido da inequação.
        indice_ca = indice_de(Nutriente.CA)
        indice_p = indice_de(Nutriente.P)
        return (
            matriz_M_sub[:, indice_ca] - alvo * matriz_M_sub[:, indice_p],
            float(contrib_fixas[indice_ca] - alvo * contrib_fixas[indice_p]),
        )

    @staticmethod
    def _validar_dimensoes(matriz_M: np.ndarray, n_ingredientes: int) -> None:
        if matriz_M.ndim != 2 or matriz_M.shape[0] != n_ingredientes:
            raise ValueError(
                "A matriz nutricional deve possuir uma linha para cada ingrediente."
            )
        if matriz_M.shape[1] != len(NUTRIENTES_ORDEM):
            raise ValueError(
                "A matriz nutricional não segue a ordem canônica de nutrientes."
            )

    @classmethod
    def _preparar_perfil_suplemento_concentrado(
        cls,
        matriz_M_sub: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
        bounds_sub: list[tuple[float, float]],
        soma_alvo: float,
        contrib_fixas: np.ndarray,
        usar_perfil_referencia: bool = False,
    ) -> tuple[list[dict], float | None, float | None]:
        """Monta alvos de referência que só entram quando forem viáveis."""
        restricoes: list[dict] = []
        pb_alvo = cls._alvo_padrao_minimo(requisitos, Nutriente.PB)
        pb_ativo = False

        if pb_alvo is not None and cls._perfil_linear_viavel(
            matriz_M_sub=matriz_M_sub,
            bounds_sub=bounds_sub,
            soma_alvo=soma_alvo,
            contrib_fixas=contrib_fixas,
            pb_alvo=pb_alvo,
        ):
            coef_pb = matriz_M_sub[:, indice_de(Nutriente.PB)].copy()
            rhs_pb = pb_alvo - contrib_fixas[indice_de(Nutriente.PB)]
            restricoes.append({
                "type": "eq",
                "fun": lambda x, c=coef_pb, alvo=rhs_pb: float(c @ x) - alvo,
                "jac": lambda x, c=coef_pb: c,
            })
            pb_ativo = True

        ndt_alvo = cls._alvo_padrao_minimo(requisitos, Nutriente.NDT)
        ndt_ativo = False
        if ndt_alvo is not None and cls._perfil_linear_viavel(
            matriz_M_sub=matriz_M_sub,
            bounds_sub=bounds_sub,
            soma_alvo=soma_alvo,
            contrib_fixas=contrib_fixas,
            pb_alvo=pb_alvo if pb_ativo else None,
            ndt_minimo=ndt_alvo,
        ):
            coef_ndt = matriz_M_sub[:, indice_de(Nutriente.NDT)].copy()
            fixo_ndt = contrib_fixas[indice_de(Nutriente.NDT)]
            restricoes.append({
                "type": "ineq",
                "fun": lambda x, c=coef_ndt, fixo=fixo_ndt, alvo=ndt_alvo: (
                    float(c @ x) + fixo - alvo
                ),
                "jac": lambda x, c=coef_ndt: c,
            })
            ndt_ativo = True

        ndt_alvo_secundario = None
        if ndt_ativo and not usar_perfil_referencia:
            valores_ndt = matriz_M_sub[:, indice_de(Nutriente.NDT)]
            maior_ndt = float(np.max(valores_ndt)) if valores_ndt.size else 0.0
            if (
                maior_ndt > 1e-12
                and ndt_alvo / maior_ndt >= cls.LIMIAR_NDT_RELATIVO_PARA_ALVO
            ):
                ndt_alvo_secundario = ndt_alvo

        ca_p_alvo = None
        if (
            not usar_perfil_referencia
            and cls._alvo_padrao_minimo(requisitos, Nutriente.CA_P) is not None
        ):
            ca_p_alvo = cls.ALVO_CA_P_SUPLEMENTO

        return restricoes, ndt_alvo_secundario, ca_p_alvo

    @staticmethod
    def _alvo_padrao_minimo(
        requisitos: dict[Nutriente, RequisitoNutriente],
        nutriente: Nutriente,
    ) -> float | None:
        requisito = requisitos.get(nutriente)
        if (
            requisito is None
            or requisito.alterado_pelo_usuario
            or requisito.valor_origem_nrc is None
            or requisito.valor_min is None
            or requisito.valor_max is not None
        ):
            return None
        return float(requisito.valor_origem_nrc)

    @staticmethod
    def _perfil_linear_viavel(
        matriz_M_sub: np.ndarray,
        bounds_sub: list[tuple[float, float]],
        soma_alvo: float,
        contrib_fixas: np.ndarray,
        pb_alvo: float | None = None,
        pb_minimo: float | None = None,
        ndt_minimo: float | None = None,
        mascara_subgrupo: np.ndarray | None = None,
        soma_subgrupo_alvo: float | None = None,
    ) -> bool:
        n = matriz_M_sub.shape[0]
        a_eq = [np.ones(n, dtype=float)]
        b_eq = [soma_alvo]

        if pb_alvo is not None:
            idx_pb = indice_de(Nutriente.PB)
            a_eq.append(matriz_M_sub[:, idx_pb])
            b_eq.append(pb_alvo - contrib_fixas[idx_pb])

        if mascara_subgrupo is not None and soma_subgrupo_alvo is not None:
            mascara = np.asarray(mascara_subgrupo, dtype=bool)
            if mascara.shape != (n,):
                return False
            if np.any(mascara) and not np.all(mascara):
                a_eq.append(mascara.astype(float))
                b_eq.append(soma_subgrupo_alvo)

        a_ub: list[np.ndarray] = []
        b_ub: list[float] = []
        if pb_minimo is not None:
            idx_pb = indice_de(Nutriente.PB)
            a_ub.append(-matriz_M_sub[:, idx_pb])
            b_ub.append(-(pb_minimo - contrib_fixas[idx_pb]))
        if ndt_minimo is not None:
            idx_ndt = indice_de(Nutriente.NDT)
            a_ub.append(-matriz_M_sub[:, idx_ndt])
            b_ub.append(-(ndt_minimo - contrib_fixas[idx_ndt]))

        try:
            resultado = linprog(
                c=np.zeros(n, dtype=float),
                A_ub=np.asarray(a_ub, dtype=float) if a_ub else None,
                b_ub=np.asarray(b_ub, dtype=float) if b_ub else None,
                A_eq=np.asarray(a_eq, dtype=float),
                b_eq=np.asarray(b_eq, dtype=float),
                bounds=bounds_sub,
                method="highs",
            )
        except ValueError:
            return False
        return bool(resultado.success)

    @classmethod
    def _pb_padrao_rigido_em_dieta_mista(
        cls,
        matriz_M_sub: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
        bounds_sub: list[tuple[float, float]],
        soma_alvo: float,
        contrib_fixas: np.ndarray,
        mascara_volumoso_sub: np.ndarray | None,
        soma_volumoso_alvo: float | None,
        dieta_mista: bool,
    ) -> bool:
        """Ativa PB padrão só para dieta com ambos os grupos e solução viável."""
        if not dieta_mista:
            return False

        pb_alvo = cls._alvo_padrao_minimo(requisitos, Nutriente.PB)
        return pb_alvo is not None and cls._perfil_linear_viavel(
            matriz_M_sub=matriz_M_sub,
            bounds_sub=bounds_sub,
            soma_alvo=soma_alvo,
            contrib_fixas=contrib_fixas,
            pb_minimo=pb_alvo,
            mascara_subgrupo=mascara_volumoso_sub,
            soma_subgrupo_alvo=soma_volumoso_alvo,
        )

    @classmethod
    def _penalidade_suplemento_concentrado(
        cls,
        x: np.ndarray,
        matriz_M_sub: np.ndarray,
        contrib_fixas: np.ndarray,
        ndt_alvo: float | None,
        ca_p_alvo: float | None,
    ) -> float:
        totais = x @ matriz_M_sub + contrib_fixas
        ndt = float(totais[indice_de(Nutriente.NDT)])
        penalidade = -cls.PESO_DENSIDADE_ENERGETICA_SUPLEMENTO * ndt / 100.0

        if ndt_alvo is not None and ndt_alvo > 1e-12:
            penalidade += cls.PESO_NDT_ALVO_SUPLEMENTO * (
                (ndt - ndt_alvo) / ndt_alvo
            ) ** 2

        if ca_p_alvo is not None:
            ca = float(totais[indice_de(Nutriente.CA)])
            fosforo = float(totais[indice_de(Nutriente.P)])
            relacao = ca / fosforo if fosforo > 1e-12 else 0.0
            penalidade += cls.PESO_CA_P_SUPLEMENTO * (
                (relacao - ca_p_alvo) / ca_p_alvo
            ) ** 2

        return float(penalidade)

    @classmethod
    def _x_alvo_suplemento_concentrado(
        cls,
        configuracoes: list[ConfiguracaoIngrediente],
        matriz_M: np.ndarray,
    ) -> np.ndarray:
        """Distribui orçamento por função e diversifica os energéticos."""
        n = len(configuracoes)
        destino = np.zeros(n, dtype=float)
        grupos: dict[str, list[int]] = {}

        for i, configuracao in enumerate(configuracoes):
            tipo = (
                configuracao.tipo
                if configuracao.tipo in cls.ORCAMENTOS_SUPLEMENTO_TIPO
                else "OUTRO"
            )
            grupos.setdefault(tipo, []).append(i)

        peso_total = sum(
            cls.ORCAMENTOS_SUPLEMENTO_TIPO[tipo]
            for tipo in grupos
        )
        if peso_total <= 0.0:
            return np.full(n, 1.0 / n, dtype=float)

        idx_fdn = indice_de(Nutriente.FDN)
        idx_ndt = indice_de(Nutriente.NDT)
        for tipo, indices in grupos.items():
            orcamento = cls.ORCAMENTOS_SUPLEMENTO_TIPO[tipo] / peso_total
            pesos = np.ones(len(indices), dtype=float)
            if tipo == "ENERGETICO":
                valores_ndt = matriz_M[indices, idx_ndt]
                maior_ndt = float(np.max(valores_ndt))
                for pos, indice in enumerate(indices):
                    fdn = float(matriz_M[indice, idx_fdn])
                    ndt = float(matriz_M[indice, idx_ndt])
                    if maior_ndt > 1e-12:
                        pesos[pos] *= np.exp(
                            (ndt - maior_ndt) / cls.ESCALA_NDT_PESO_ENERGETICO
                        )
                    if fdn > cls.FDN_LIMIAR_ENERGETICO_SUPLEMENTO:
                        pesos[pos] *= (
                            cls.FDN_LIMIAR_ENERGETICO_SUPLEMENTO / fdn
                        ) ** cls.EXPOENTE_PENALIDADE_FIBRA_ENERGETICO
            pesos /= pesos.sum()
            destino[indices] = pesos * orcamento

        return destino

    @classmethod
    def _preparar_x_alvo(
        cls,
        configuracoes: list[ConfiguracaoIngrediente],
        percentual_volumoso: float,
        matriz_M: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
        permitir_perfil_referencia: bool = True,
        contexto_zootecnico: ContextoZootecnico | None = None,
        referencias_suplemento: tuple[ReferenciaSuplemento, ...] = (),
    ) -> tuple[np.ndarray, bool, str, float | None]:
        """Monta a âncora heurística ou uma guia validada, sempre auditável."""
        if (
            permitir_perfil_referencia
            and contexto_zootecnico is not None
            and referencias_suplemento
        ):
            estimado = cls._x_alvo_estimado_contexto(
                configuracoes=configuracoes,
                matriz_M=matriz_M,
                requisitos=requisitos,
                contexto_zootecnico=contexto_zootecnico,
                referencias_suplemento=referencias_suplemento,
            )
            if estimado is not None:
                destino, confianca, exata, origem = estimado
                return (
                    destino,
                    exata,
                    f"referencia_validada_exata:{origem}" if exata else origem,
                    confianca,
                )
        return (
            cls._x_alvo_heuristico(
                configuracoes=configuracoes,
                percentual_volumoso=percentual_volumoso,
                matriz_M=matriz_M,
            ),
            False,
            "heuristica_funcional",
            None,
        )

    @classmethod
    def _x_alvo_estimado_contexto(
        cls,
        configuracoes: list[ConfiguracaoIngrediente],
        matriz_M: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
        contexto_zootecnico: ContextoZootecnico,
        referencias_suplemento: tuple[ReferenciaSuplemento, ...],
    ) -> tuple[np.ndarray, float, bool, str] | None:
        if any(
            configuracao.classificacao == "VOLUMOSO"
            for configuracao in configuracoes
        ):
            return None

        estimativa = EstimadorReceitaReferencia.estimar(
            contexto=contexto_zootecnico,
            requisitos=requisitos,
            referencias=referencias_suplemento,
        )
        if estimativa is None:
            return None

        if not estimativa.exata:
            preferencia_aprendida = EstimadorPreferenciaAprendida.estimar(
                contexto=contexto_zootecnico,
                requisitos=requisitos,
                matriz_M=matriz_M,
                classificacoes=tuple(cfg.classificacao for cfg in configuracoes),
                tipos=tuple(cfg.tipo for cfg in configuracoes),
                limites_max=tuple(cfg.limite_max for cfg in configuracoes),
                referencias=referencias_suplemento,
                confianca_contextual=estimativa.confianca,
            )
            if (
                preferencia_aprendida is not None
                and preferencia_aprendida.confianca >= cls.CONFIANCA_MINIMA_ESTIMADOR
            ):
                heuristica = cls._x_alvo_suplemento_concentrado(
                    configuracoes, matriz_M
                )
                peso_aprendido = min(0.85, preferencia_aprendida.confianca)
                destino = (
                    peso_aprendido * preferencia_aprendida.fracoes
                    + (1.0 - peso_aprendido) * heuristica
                )
                destino /= float(destino.sum())
                return (
                    destino,
                    preferencia_aprendida.confianca,
                    False,
                    "preferencia_aprendida",
                )

        # A mesma exigência pode possuir receitas diferentes no livro. A
        # composição e o tipo dos ingredientes selecionados desempata, sem
        # observar ID, nome, nem a posição em que o usuário os escolheu.
        melhor = None
        for referencia in estimativa.referencias_ordenadas:
            mapeada = cls._mapear_referencia_validada(
                referencia=referencia,
                configuracoes=configuracoes,
                matriz_M=matriz_M,
            )
            if mapeada is None:
                continue
            destino_referencia, cobertura = mapeada
            pontuacao = cobertura * exp(-EstimadorReceitaReferencia._distancia(
                contexto_zootecnico,
                EstimadorReceitaReferencia._vetor_exigencias(requisitos),
                referencia,
            ))
            if melhor is None or pontuacao > melhor[0]:
                melhor = (pontuacao, referencia, destino_referencia, cobertura)
        if melhor is None:
            return None

        _, referencia, destino_referencia, cobertura = melhor
        exata = estimativa.exata and cobertura >= 0.98
        confianca = float(np.clip(estimativa.confianca * cobertura, 0.0, 1.0))
        if not exata and confianca < cls.CONFIANCA_MINIMA_ESTIMADOR:
            return None

        heuristica = cls._x_alvo_suplemento_concentrado(configuracoes, matriz_M)
        peso_referencia = 1.0 if exata else min(0.85, confianca)
        destino = peso_referencia * destino_referencia + (1.0 - peso_referencia) * heuristica
        destino /= float(destino.sum())
        origem = (
            f"referencia_validada_guia:{referencia.codigo}"
            if not exata else referencia.codigo
        )
        return destino, confianca, exata, origem

    @classmethod
    def _mapear_referencia_validada(
        cls,
        referencia: ReferenciaSuplemento,
        configuracoes: list[ConfiguracaoIngrediente],
        matriz_M: np.ndarray,
    ) -> tuple[np.ndarray, float] | None:
        """Projeta uma referência para os itens escolhidos por função e composição."""
        if not referencia.ingredientes:
            return None
        destino = np.zeros(len(configuracoes), dtype=float)
        cobertura = 0.0
        usados: set[int] = set()
        componentes = sorted(
            referencia.ingredientes,
            key=lambda item: item.participacao,
            reverse=True,
        )
        for componente in componentes:
            candidatos = [
                indice for indice, configuracao in enumerate(configuracoes)
                if indice not in usados
                and configuracao.classificacao == componente.classificacao
                and configuracao.tipo == componente.tipo
            ]
            if not candidatos:
                return None
            if componente.tipo == "ADITIVOS":
                # A composição dos aditivos é nula; o limite técnico é a
                # informação funcional que permite distingui-los.
                indice = max(candidatos, key=lambda item: configuracoes[item].limite_max)
                similaridade = 1.0
            else:
                similaridades = [
                    cls._similaridade_composicao_vetores(
                        matriz_M[indice], componente.composicao
                    )
                    for indice in candidatos
                ]
                posicao = int(np.argmax(similaridades))
                indice = candidatos[posicao]
                similaridade = float(similaridades[posicao])
            usados.add(indice)
            destino[indice] += componente.participacao
            cobertura += componente.participacao * similaridade
        if destino.sum() <= 1e-12:
            return None
        # Uma receita com o mesmo contexto, mas que não contém todos os tipos
        # selecionados, não pode se passar por uma correspondência exata. Isso
        # também desambigua casos do livro com a mesma linha NRC e diferentes
        # fontes energéticas, sem recorrer a nomes ou IDs.
        contagem_referencia: dict[str, int] = {}
        contagem_selecionada: dict[str, int] = {}
        for componente in componentes:
            contagem_referencia[componente.tipo] = (
                contagem_referencia.get(componente.tipo, 0) + 1
            )
        for configuracao in configuracoes:
            contagem_selecionada[configuracao.tipo] = (
                contagem_selecionada.get(configuracao.tipo, 0) + 1
            )
        fatores = [
            min(contagem_referencia.get(tipo, 0), contagem_selecionada.get(tipo, 0))
            / max(contagem_referencia.get(tipo, 0), contagem_selecionada.get(tipo, 0))
            for tipo in set(contagem_referencia) | set(contagem_selecionada)
        ]
        cobertura *= min(fatores, default=0.0)
        return destino / float(destino.sum()), float(np.clip(cobertura, 0.0, 1.0))

    @staticmethod
    def _similaridade_composicao_vetores(
        composicao: np.ndarray,
        referencia: tuple[float, float, float, float, float, float],
    ) -> float:
        indices = [indice_de(nutriente) for nutriente in (
            Nutriente.PB, Nutriente.NDT, Nutriente.FDN, Nutriente.EE,
            Nutriente.CA, Nutriente.P,
        )]
        observado = np.asarray(composicao[indices], dtype=float)
        esperado = np.asarray(referencia, dtype=float)
        escalas = np.maximum(np.abs(esperado) * 0.25, np.array([2.0, 5.0, 5.0, 1.0, 0.20, 0.10]))
        distancia = float(np.sqrt(np.mean(np.square((observado - esperado) / escalas))))
        return float(np.exp(-distancia))

    @classmethod
    def _similaridade_composicao(
        cls,
        composicao: np.ndarray,
        assinatura: str,
    ) -> float:
        referencia = np.asarray(
            cls.ASSINATURAS_INGREDIENTES_REFERENCIA[assinatura],
            dtype=float,
        )
        indices = [
            indice_de(nutriente)
            for nutriente in (
                Nutriente.PB,
                Nutriente.NDT,
                Nutriente.FDN,
                Nutriente.EE,
                Nutriente.CA,
                Nutriente.P,
            )
        ]
        observado = np.asarray(composicao[indices], dtype=float)
        escalas_minimas = np.array([2.0, 5.0, 5.0, 1.0, 0.20, 0.10])
        escalas = np.maximum(np.abs(referencia) * 0.25, escalas_minimas)
        distancia = float(np.sqrt(np.mean(np.square(
            (observado - referencia) / escalas
        ))))
        return float(np.exp(-distancia))

    @classmethod
    def _x_alvo_referencia_suplemento(
        cls,
        configuracoes: list[ConfiguracaoIngrediente],
        matriz_M: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
    ) -> np.ndarray | None:
        """Reconhece os conjuntos de ingredientes publicados no manual."""
        if any(
            configuracao.classificacao == "VOLUMOSO"
            for configuracao in configuracoes
        ):
            return None

        perfil_completo = cls._x_alvo_referencia_suplemento_completo(
            configuracoes=configuracoes,
            matriz_M=matriz_M,
            requisitos=requisitos,
        )
        if perfil_completo is not None:
            return perfil_completo

        return cls._x_alvo_referencia_suplemento_quatro_ingredientes(
            configuracoes=configuracoes,
            matriz_M=matriz_M,
            requisitos=requisitos,
        )

    @classmethod
    def _x_alvo_referencia_suplemento_completo(
        cls,
        configuracoes: list[ConfiguracaoIngrediente],
        matriz_M: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
    ) -> np.ndarray | None:
        grupos: dict[str, list[int]] = {}
        for indice, configuracao in enumerate(configuracoes):
            grupos.setdefault(configuracao.tipo, []).append(indice)
        if (
            len(configuracoes) != 8
            or len(grupos.get("ENERGETICO", [])) != 4
            or len(grupos.get("PROTEICO", [])) != 1
            or len(grupos.get("MINERAL", [])) != 1
            or len(grupos.get("ADITIVOS", [])) != 2
            or set(grupos) != {"ENERGETICO", "PROTEICO", "MINERAL", "ADITIVOS"}
        ):
            return None

        pb_alvo = cls._alvo_padrao_minimo(requisitos, Nutriente.PB)
        ndt_alvo = cls._alvo_padrao_minimo(requisitos, Nutriente.NDT)
        if pb_alvo is None or ndt_alvo is None:
            return None

        perfil = cls._selecionar_perfil_referencia(
            perfis=cls.PERFIS_REFERENCIA_SUPLEMENTO_COMPLETO,
            pb_alvo=pb_alvo,
            ndt_alvo=ndt_alvo,
        )
        if perfil is None:
            return None

        tipo_por_assinatura = {
            "MILHO": "ENERGETICO",
            "AVEIA": "ENERGETICO",
            "SORGO": "ENERGETICO",
            "MELACO": "ENERGETICO",
            "SOJA": "PROTEICO",
            "CALCARIO": "MINERAL",
        }
        indices_por_assinatura: dict[str, int] = {}
        indices_disponiveis = {
            tipo: list(indices) for tipo, indices in grupos.items()
        }
        for assinatura in cls.ASSINATURAS_PERFIL_COMPLETO:
            tipo = tipo_por_assinatura[assinatura]
            correspondentes = [
                indice
                for indice in indices_disponiveis[tipo]
                if cls._composicao_corresponde(matriz_M[indice], assinatura)
            ]
            if len(correspondentes) != 1:
                return None
            indice = correspondentes[0]
            indices_por_assinatura[assinatura] = indice
            indices_disponiveis[tipo].remove(indice)

        # Os dois aditivos não possuem contribuição nos nutrientes atualmente
        # modelados. Eles são distinguidos pelos limites técnicos cadastrados:
        # bicarbonato até 1% e cloreto até 0,5%.
        indices_aditivos = sorted(
            grupos["ADITIVOS"],
            key=lambda indice: configuracoes[indice].limite_max,
            reverse=True,
        )
        limites_aditivos = [
            configuracoes[indice].limite_max for indice in indices_aditivos
        ]
        if not np.allclose(limites_aditivos, (0.010, 0.005), atol=1e-9, rtol=0.0):
            return None

        destino = np.zeros(len(configuracoes), dtype=float)
        receita = perfil[2]
        for posicao, assinatura in enumerate(cls.ASSINATURAS_PERFIL_COMPLETO):
            destino[indices_por_assinatura[assinatura]] = receita[posicao]
        destino[indices_aditivos[0]] = receita[-2]
        destino[indices_aditivos[1]] = receita[-1]
        return destino

    @classmethod
    def _x_alvo_referencia_suplemento_quatro_ingredientes(
        cls,
        configuracoes: list[ConfiguracaoIngrediente],
        matriz_M: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
    ) -> np.ndarray | None:

        grupos: dict[str, list[int]] = {}
        for indice, configuracao in enumerate(configuracoes):
            grupos.setdefault(configuracao.tipo, []).append(indice)
        if (
            len(configuracoes) != 4
            or len(grupos.get("ENERGETICO", [])) != 2
            or len(grupos.get("PROTEICO", [])) != 1
            or len(grupos.get("MINERAL", [])) != 1
            or set(grupos) != {"ENERGETICO", "PROTEICO", "MINERAL"}
        ):
            return None

        pb_alvo = cls._alvo_padrao_minimo(requisitos, Nutriente.PB)
        ndt_alvo = cls._alvo_padrao_minimo(requisitos, Nutriente.NDT)
        if pb_alvo is None or ndt_alvo is None:
            return None

        perfil = cls._selecionar_perfil_referencia(
            perfis=cls.PERFIS_REFERENCIA_SUPLEMENTO,
            pb_alvo=pb_alvo,
            ndt_alvo=ndt_alvo,
        )
        if perfil is None:
            return None

        idx_proteico = grupos["PROTEICO"][0]
        idx_mineral = grupos["MINERAL"][0]
        if not cls._composicao_corresponde(
            matriz_M[idx_proteico], "SOJA"
        ) or not cls._composicao_corresponde(matriz_M[idx_mineral], "CALCARIO"):
            return None

        idx_energeticos = grupos["ENERGETICO"]
        valores_fdn = matriz_M[idx_energeticos, indice_de(Nutriente.FDN)]
        if float(np.max(valores_fdn)) > cls.FDN_LIMIAR_ENERGETICO_SUPLEMENTO:
            ordem_energia = sorted(
                idx_energeticos,
                key=lambda indice: matriz_M[indice, indice_de(Nutriente.FDN)],
                reverse=True,
            )
            assinaturas = ("TRIGO", "MILHO")
            receita = perfil[2]
        else:
            ordem_energia = sorted(
                idx_energeticos,
                key=lambda indice: matriz_M[indice, indice_de(Nutriente.NDT)],
                reverse=True,
            )
            assinaturas = ("MILHO", "AVEIA")
            receita = perfil[3]

        if any(
            not cls._composicao_corresponde(matriz_M[indice], assinatura)
            for indice, assinatura in zip(ordem_energia, assinaturas)
        ):
            return None

        destino = np.zeros(len(configuracoes), dtype=float)
        destino[ordem_energia[0]] = receita[0]
        destino[ordem_energia[1]] = receita[1]
        destino[idx_proteico] = receita[2]
        destino[idx_mineral] = receita[3]
        return destino

    @classmethod
    def _selecionar_perfil_referencia(
        cls,
        perfis: tuple[tuple, ...],
        pb_alvo: float,
        ndt_alvo: float,
    ) -> tuple | None:
        candidatos = [
            perfil
            for perfil in perfis
            if abs(pb_alvo - perfil[0]) <= cls.TOLERANCIA_PB_PERFIL_REFERENCIA
            and abs(ndt_alvo - perfil[1]) <= cls.TOLERANCIA_NDT_PERFIL_REFERENCIA
        ]
        if not candidatos:
            return None
        return min(
            candidatos,
            key=lambda item: (
                abs(pb_alvo - item[0]) / cls.TOLERANCIA_PB_PERFIL_REFERENCIA
                + abs(ndt_alvo - item[1]) / cls.TOLERANCIA_NDT_PERFIL_REFERENCIA
            ),
        )

    @classmethod
    def _composicao_corresponde(
        cls,
        composicao: np.ndarray,
        assinatura: str,
    ) -> bool:
        referencia = np.asarray(
            cls.ASSINATURAS_INGREDIENTES_REFERENCIA[assinatura],
            dtype=float,
        )
        indices = [
            indice_de(nutriente)
            for nutriente in (
                Nutriente.PB,
                Nutriente.NDT,
                Nutriente.FDN,
                Nutriente.EE,
                Nutriente.CA,
                Nutriente.P,
            )
        ]
        observado = np.asarray(composicao[indices], dtype=float)
        return bool(np.allclose(
            observado,
            referencia,
            rtol=cls.RTOL_ASSINATURA_INGREDIENTE,
            atol=cls.ATOL_ASSINATURA_INGREDIENTE,
        ))

    @classmethod
    def _x_alvo_heuristico(
        cls,
        configuracoes: list[ConfiguracaoIngrediente],
        percentual_volumoso: float,
        matriz_M: np.ndarray | None = None,
    ) -> np.ndarray:
        """
        Distribuição-alvo heurística:
        - Volumosos dividem o orçamento da classe uniformemente.
        - Concentrados recebem pesos por função (energético, proteico,
          mineral e aditivo), evitando uma divisão inicial artificialmente
          igual entre milho, ureia e calcário.
        - Se só existir uma classe, ela ocupa toda a formulação.
        """
        n = len(configuracoes)
        idx_vol  = [i for i, c in enumerate(configuracoes) if c.classificacao == "VOLUMOSO"]
        idx_conc = [i for i, c in enumerate(configuracoes) if c.classificacao != "VOLUMOSO"]

        x = np.zeros(n, dtype=float)

        if not idx_vol and matriz_M is not None:
            # Esta âncora serve só como ponto inicial numérico. Sua influência
            # no objetivo é deliberadamente pequena; a escolha final vem dos
            # nutrientes, dos operadores e dos limites de inclusão.
            return cls._x_alvo_suplemento_concentrado(
                configuracoes=configuracoes,
                matriz_M=matriz_M,
            )

        if idx_vol and idx_conc:
            cls._distribuir_orcamento(x, idx_vol, percentual_volumoso, configuracoes)
            cls._distribuir_orcamento(x, idx_conc, 1.0 - percentual_volumoso, configuracoes)
        elif idx_vol:
            cls._distribuir_orcamento(x, idx_vol, 1.0, configuracoes)
        else:
            cls._distribuir_orcamento(x, idx_conc, 1.0, configuracoes)

        return x

    @classmethod
    def _distribuir_orcamento(
        cls,
        destino: np.ndarray,
        indices: list[int],
        orcamento: float,
        configuracoes: list[ConfiguracaoIngrediente],
    ) -> None:
        if not indices or orcamento <= 0.0:
            return

        pesos = np.array([
            1.0
            if configuracoes[i].classificacao == "VOLUMOSO"
            else cls.PESOS_HEURISTICOS_TIPO.get(
                configuracoes[i].tipo,
                cls.PESOS_HEURISTICOS_TIPO["OUTRO"],
            )
            for i in indices
        ], dtype=float)
        pesos /= pesos.sum()
        destino[indices] = pesos * orcamento

    @staticmethod
    def _normalizar_percentual_volumoso(valor: float) -> float:
        valor = float(valor)
        valor = valor / 100.0 if valor > 1.0 else valor
        return max(0.0, min(1.0, valor))

    @staticmethod
    def _normalizar_objetivo(
        objetivo: ObjetivoGeracao | str,
    ) -> ObjetivoGeracao:
        if isinstance(objetivo, ObjetivoGeracao):
            return objetivo
        try:
            return ObjetivoGeracao(str(objetivo).upper())
        except ValueError as exc:
            opcoes = ", ".join(item.value for item in ObjetivoGeracao)
            raise ValueError(f"Objetivo inválido. Use: {opcoes}.") from exc

    @staticmethod
    def _custos_configuracoes(
        configuracoes: list[ConfiguracaoIngrediente],
    ) -> np.ndarray:
        return np.asarray([
            config.custo_por_kg_ms or 0.0 for config in configuracoes
        ], dtype=float)

    @staticmethod
    def _mascara_volumoso(configuracoes: list[ConfiguracaoIngrediente]) -> np.ndarray:
        return np.array([c.classificacao == "VOLUMOSO" for c in configuracoes], dtype=bool)

    @classmethod
    def _perfil_nutricional(
        cls,
        configuracoes: list[ConfiguracaoIngrediente],
    ) -> PerfilNutricional:
        """Distingue dieta total de suplemento pela presença de volumoso."""
        if bool(np.any(cls._mascara_volumoso(configuracoes))):
            return PerfilNutricional.DIETA_TOTAL
        return PerfilNutricional.SUPLEMENTO_CONCENTRADO

    @classmethod
    def _tem_volumoso_e_concentrado(
        cls,
        configuracoes: list[ConfiguracaoIngrediente],
    ) -> bool:
        mascara_volumoso = cls._mascara_volumoso(configuracoes)
        return bool(np.any(mascara_volumoso) and np.any(~mascara_volumoso))

    @classmethod
    def _bounds_geracao(
        cls,
        configuracoes: list[ConfiguracaoIngrediente],
        soma_total: float,
        percentual_volumoso: float | None,
        aplicar_piso_tecnico: bool = True,
    ) -> list[tuple[float, float]]:
        """Aplica um piso técnico aos ingredientes selecionados quando viável."""
        if not configuracoes:
            return []

        mascara_vol = cls._mascara_volumoso(configuracoes)
        tem_vol = bool(np.any(mascara_vol))
        tem_conc = bool(np.any(~mascara_vol))

        if tem_vol and tem_conc and percentual_volumoso is not None:
            orcamentos = {
                True: soma_total * percentual_volumoso,
                False: soma_total * (1.0 - percentual_volumoso),
            }
        elif tem_vol:
            orcamentos = {True: soma_total, False: 0.0}
        else:
            orcamentos = {True: 0.0, False: soma_total}

        bounds = [
            [config.limite_min, min(config.limite_max, soma_total)]
            for config in configuracoes
        ]
        if not aplicar_piso_tecnico:
            return [(float(lo), float(hi)) for lo, hi in bounds]

        for e_volumoso, orcamento in orcamentos.items():
            indices = [
                i for i, marcado in enumerate(mascara_vol)
                if bool(marcado) is e_volumoso and bounds[i][1] > 0.0
            ]
            if not indices or orcamento <= 0.0:
                continue

            piso = min(
                cls.MINIMO_TECNICO_GERACAO,
                orcamento / (2.0 * len(indices)),
            )
            for i in indices:
                bounds[i][0] = max(bounds[i][0], min(piso, bounds[i][1]))

        return [(float(lo), float(hi)) for lo, hi in bounds]

    @staticmethod
    def _validar_soma_subgrupo_viavel(
        bounds_sub: list[tuple[float, float]],
        mascara: np.ndarray,
        soma_alvo: float,
        soma_total_alvo: float,
        nome: str,
    ) -> float:
        if not np.any(mascara):
            if abs(soma_alvo) <= 1e-9:
                return 0.0
            raise ValueError(f"Nenhum ingrediente {nome} foi selecionado para atingir o alvo.")

        if np.all(mascara):
            if abs(soma_alvo - soma_total_alvo) <= 1e-9:
                return soma_alvo
            raise ValueError(
                f"Alvo de {nome} inviável: todos os ingredientes selecionados "
                f"são {nome}s, portanto eles precisam ocupar "
                f"{soma_total_alvo * 100:.2f}% da formulação."
            )

        minimo = sum(bounds_sub[i][0] for i, marcado in enumerate(mascara) if marcado)
        maximo = sum(bounds_sub[i][1] for i, marcado in enumerate(mascara) if marcado)
        if soma_alvo < minimo - 1e-9 or soma_alvo > maximo + 1e-9:
            raise ValueError(
                f"Alvo de {nome} inviável: solicitado {soma_alvo * 100:.2f}%, "
                f"mas os limites permitem de {minimo * 100:.2f}% a {maximo * 100:.2f}%."
            )
        minimo_complemento = sum(
            bounds_sub[i][0] for i, marcado in enumerate(mascara) if not marcado
        )
        maximo_complemento = sum(
            bounds_sub[i][1] for i, marcado in enumerate(mascara) if not marcado
        )
        alvo_complemento = soma_total_alvo - soma_alvo
        if (
            alvo_complemento < minimo_complemento - 1e-9
            or alvo_complemento > maximo_complemento + 1e-9
        ):
            raise ValueError(
                f"Alvo de {nome} inviável: o restante da fórmula precisa somar "
                f"{alvo_complemento * 100:.2f}%, mas os limites permitem de "
                f"{minimo_complemento * 100:.2f}% a {maximo_complemento * 100:.2f}%."
            )
        return soma_alvo

    @classmethod
    def _projetar_estrutura(
        cls,
        x: np.ndarray,
        soma_alvo: float,
        bounds: list[tuple[float, float]],
        mascara_subgrupo: np.ndarray | None,
        soma_subgrupo_alvo: float | None,
    ) -> np.ndarray:
        """Projeta soma total e, quando aplicável, a soma do subgrupo."""
        if (
            mascara_subgrupo is None
            or soma_subgrupo_alvo is None
            or not np.any(mascara_subgrupo)
            or np.all(mascara_subgrupo)
        ):
            return cls._projetar_soma(x, soma_alvo, bounds)

        mascara = np.asarray(mascara_subgrupo, dtype=bool)
        complemento = ~mascara
        resultado = np.zeros_like(np.asarray(x, dtype=float))
        resultado[mascara] = cls._projetar_soma(
            np.asarray(x, dtype=float)[mascara],
            soma_subgrupo_alvo,
            [bounds[i] for i in np.where(mascara)[0]],
        )
        resultado[complemento] = cls._projetar_soma(
            np.asarray(x, dtype=float)[complemento],
            soma_alvo - soma_subgrupo_alvo,
            [bounds[i] for i in np.where(complemento)[0]],
        )
        return resultado

    @staticmethod
    def _projetar_soma(
        x: np.ndarray,
        soma_alvo: float,
        bounds: list[tuple[float, float]],
    ) -> np.ndarray:
        """
        Projeta x para que sum(x) == soma_alvo, respeitando os bounds.
        Usado para fornecer um x0 viável ao SLSQP.
        """
        n = len(x)
        if n == 0:
            return x

        lbs = np.array([b[0] for b in bounds], dtype=float)
        ubs = np.array([b[1] for b in bounds], dtype=float)
        min_soma = float(lbs.sum())
        max_soma = float(ubs.sum())
        if soma_alvo < min_soma - 1e-9 or soma_alvo > max_soma + 1e-9:
            raise ValueError(
                f"Soma alvo inviável: precisa fechar {soma_alvo * 100:.2f}%, "
                f"mas os limites dos ingredientes permitem de "
                f"{min_soma * 100:.2f}% a {max_soma * 100:.2f}%."
            )

        x = np.clip(np.asarray(x, dtype=float), lbs, ubs)
        for _ in range(100):
            residual = float(soma_alvo - x.sum())
            if abs(residual) <= 1e-12:
                break

            if residual > 0:
                capacidade = ubs - x
                livres = capacidade > 1e-12
                total_capacidade = float(capacidade[livres].sum())
                if total_capacidade <= 1e-12:
                    break
                incremento = np.minimum(
                    capacidade[livres],
                    capacidade[livres] / total_capacidade * residual,
                )
                x[livres] += incremento
            else:
                capacidade = x - lbs
                livres = capacidade > 1e-12
                total_capacidade = float(capacidade[livres].sum())
                if total_capacidade <= 1e-12:
                    break
                decremento = np.minimum(
                    capacidade[livres],
                    capacidade[livres] / total_capacidade * (-residual),
                )
                x[livres] -= decremento

        residual = float(soma_alvo - x.sum())
        if abs(residual) > 1e-12:
            if residual > 0:
                livres = np.where((ubs - x) >= residual - 1e-10)[0]
            else:
                livres = np.where((x - lbs) >= (-residual) - 1e-10)[0]
            if len(livres):
                x[livres[0]] += residual

        x = np.clip(x, lbs, ubs)

        # O SLSQP pode devolver resíduos como 2e-16 para uma variável cujo
        # limite inferior é zero. Embora isso seja numericamente equivalente
        # a zero, o JSON o expõe em notação científica e induz a leitura de
        # "2e-16" como "2". Canonizamos valores colados aos limites e
        # transferimos o resíduo para uma variável com capacidade, preservando
        # simultaneamente a soma e os bounds.
        tolerancia_canonica = 1e-12
        proximos_do_minimo = np.abs(x - lbs) <= tolerancia_canonica
        proximos_do_maximo = np.abs(x - ubs) <= tolerancia_canonica
        x[proximos_do_minimo] = lbs[proximos_do_minimo]
        x[proximos_do_maximo] = ubs[proximos_do_maximo]

        residual = float(soma_alvo - x.sum())
        if residual != 0.0:
            capacidade = (ubs - x) if residual > 0 else (x - lbs)
            candidatos = np.where(capacidade > 0.0)[0]
            if len(candidatos):
                # Ao acrescentar um resíduo positivo, prefira uma participação
                # já significativa. Escolher a maior capacidade poderia
                # recolocar 2e-16 justamente no ingrediente recém-zerado.
                criterio = x[candidatos] if residual > 0 else capacidade[candidatos]
                idx = int(candidatos[np.argmax(criterio)])
                x[idx] += residual

        x = np.clip(x, lbs, ubs)
        if abs(float(x.sum()) - soma_alvo) > 1e-10:
            raise RuntimeError("Falha interna ao projetar participações para a soma alvo.")
        return x
