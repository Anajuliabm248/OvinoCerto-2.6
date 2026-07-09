"""

Resolve dois problemas de viabilidade (seção 9 e 11 do documento
de arquitetura) usando scipy.optimize.minimize (SLSQP):

  1. gerar_distribuicao_inicial(): dado um conjunto de ingredientes
     e requisitos nutricionais, encontra um vetor de participações
     x que soma 1 e tenta satisfazer todos os requisitos.

  2. redistribuir(): dado que alguns ingredientes estão travados
     (MANUAL_TRAVADA), redistribui as participações dos livres
     (CALCULADA) no espaço restante (1 - Σ travados).

Objetivo em ambos os casos: minimizar ‖x - x_alvo‖² (quadrado do módulo da diferença)
(menor desvio possível em relação a uma distribuição-alvo heurística),
sem qualquer função de custo econômico.

Se SLSQP não convergir, usa nnls como fallback para encontrar a
melhor aproximação possível (menor violação total) — nunca bloqueia.

O SLSQP é um algoritmo usado para resolver problemas de otimização não linear
com a possibilidade de aplicar restrições e limites. Nele definimos:
1. Uma função objetivo (que o algoritmo tentará minimizar).
2. As restrições (iguais, maiores ou menores que zero).
3. Os limites (bounds) para as variáveis.

ele garante que o desvio final seja muito menor do que por simplex, já que 
por ser uma função quadrática, ela é ainda mais brutal na penalidade do desvio
(o dobro), assim a distribuição final fica o mais parecida possível com a 
distribuição desejada
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize, nnls
from scipy.optimize import Bounds

from formulacao.domain.nutrientes import NUTRIENTES_ORDEM, Nutriente, indice_de
from formulacao.domain.participacao import OrigemParticipacao, ParticipacaoVetor
from formulacao.domain.requisito import RequisitoNutriente



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

    def __post_init__(self) -> None:
        if not (0.0 <= self.limite_min <= self.limite_max <= 1.0):
            raise ValueError(
                f"ConfiguracaoIngrediente: limites inválidos "
                f"[{self.limite_min}, {self.limite_max}]"
            )


@dataclass(frozen=True)
class ResultadoDistribuicao:
    """
    Resultado do MotorAdequacao.

    fracoes    : vetor de participações em 0-1, indexado da mesma
                 forma que os inputs.
    convergiu  : True se o SLSQP convergiu dentro das tolerâncias.
                 False indica "melhor esforço" — MotorAlertas reportará
                 as restrições ainda violadas.
    mensagem   : descrição do status do solver para log/auditoria.
    """
    fracoes: np.ndarray = field(repr=False)
    convergiu: bool
    mensagem: str


# Motor

class MotorAdequacao:

    # Percentual-alvo de volumosos na distribuição heurística inicial.
    PERCENTUAL_ALVO_VOLUMOSO: float = 0.50

    # Variação máxima por ingrediente livre em uma redistribuição.
    # Evita "saltos" visuais (seção 11).
    VARIACAO_MAX_POR_ITERACAO: float = 0.10

    # Tolerância do SLSQP
    SLSQP_FTOL: float = 1e-9
    SLSQP_MAXITER: int = 1000

    
    # API pública
    

    @classmethod
    def gerar_distribuicao_inicial(
        cls,
        matriz_M: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
        configuracoes: list[ConfiguracaoIngrediente],
        percentual_alvo_volumoso: float | None = None,
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

        alvo_vol = percentual_alvo_volumoso if percentual_alvo_volumoso is not None \
                   else cls.PERCENTUAL_ALVO_VOLUMOSO

        x_alvo = cls._x_alvo_heuristico(configuracoes, alvo_vol)
        bounds  = [(c.limite_min, c.limite_max) for c in configuracoes]

        return cls._resolver(
            n=n,
            matriz_M_sub=matriz_M,
            requisitos=requisitos,
            x_alvo_sub=x_alvo,
            bounds_sub=bounds,
            soma_alvo=1.0,
            contrib_fixas=np.zeros(len(NUTRIENTES_ORDEM)),
        )

    @classmethod
    def redistribuir(
        cls,
        matriz_M: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
        participacao_atual: ParticipacaoVetor,
        configuracoes: list[ConfiguracaoIngrediente],
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
        mascara_travados = participacao_atual.mascara_travados()
        mascara_livres   = participacao_atual.mascara_livres()

        espaco_livre = participacao_atual.espaco_livre()
        if espaco_livre <= 1e-9:
            return ResultadoDistribuicao(
                fracoes=participacao_atual.fracoes.copy(),
                convergiu=False,
                mensagem=(
                    f"Espaço livre = {espaco_livre:.4f}: participações travadas "
                    f"já somam {participacao_atual.soma_travados()*100:.1f}%. "
                    "Destravar algum ingrediente para redistribuir."
                ),
            )

        indices_livres = np.where(mascara_livres)[0]
        n_livres = len(indices_livres)

        if n_livres == 0:
            return ResultadoDistribuicao(
                fracoes=participacao_atual.fracoes.copy(),
                convergiu=True,
                mensagem="Nenhum ingrediente livre para redistribuir.",
            )

        # Caso trivial: único ingrediente livre
        if n_livres == 1:
            fracoes_resultado = participacao_atual.fracoes.copy()
            fracoes_resultado[indices_livres[0]] = espaco_livre
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
        if soma_livres_atual > 1e-9:
            x_alvo_livres = fracoes_livres_atuais / soma_livres_atual * espaco_livre
        else:
            x_alvo_livres = cls._x_alvo_heuristico(cfg_livres, cls.PERCENTUAL_ALVO_VOLUMOSO)
            x_alvo_livres = x_alvo_livres * espaco_livre

        # Bounds dinâmicos: limite de variação máxima por iteração
        bounds_livres = []
        for i, idx_global in enumerate(indices_livres):
            cfg = configuracoes[idx_global]
            fracao_atual = participacao_atual.fracoes[idx_global]
            lo = max(cfg.limite_min, fracao_atual - cls.VARIACAO_MAX_POR_ITERACAO)
            hi = min(
                min(cfg.limite_max, espaco_livre),
                fracao_atual + cls.VARIACAO_MAX_POR_ITERACAO,
            )
            # Garante lo <= hi (pode ocorrer se fracao_atual == 0)
            lo = min(lo, hi)
            bounds_livres.append((lo, hi))

        resultado_livres = cls._resolver(
            n=n_livres,
            matriz_M_sub=M_livres,
            requisitos=requisitos,
            x_alvo_sub=x_alvo_livres,
            bounds_sub=bounds_livres,
            soma_alvo=espaco_livre,
            contrib_fixas=contrib_fixas,
        )

        # Recompor vetor completo
        fracoes_resultado = participacao_atual.fracoes.copy()
        fracoes_resultado[indices_livres] = resultado_livres.fracoes

        return ResultadoDistribuicao(
            fracoes=fracoes_resultado,
            convergiu=resultado_livres.convergiu,
            mensagem=resultado_livres.mensagem,
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
    ) -> ResultadoDistribuicao:
        """
        Núcleo do otimizador. Opera apenas sobre o subconjunto de
        ingredientes relevante (todos ou só os livres).

        contrib_fixas: contribuição nutricional já fixada pelos
        ingredientes travados (shape N_NUTRIENTES). Ajusta o RHS das
        restrições para que o solver opere apenas sobre os livres.
        """
        def objetivo(x: np.ndarray) -> float:
            diff = x - x_alvo_sub
            return float(diff @ diff)

        def grad_objetivo(x: np.ndarray) -> np.ndarray:
            return 2.0 * (x - x_alvo_sub)

        constraints = [
            {
                "type": "eq",
                "fun": lambda x: float(np.sum(x)) - soma_alvo,
                "jac": lambda x: np.ones(n),
            }
        ]

        for nutriente, requisito in requisitos.items():
            lo, hi = requisito.limites_lp()

            if nutriente == Nutriente.CA_P:
                cls._adicionar_restricoes_relacao_ca_p(
                    constraints=constraints,
                    matriz_M_sub=matriz_M_sub,
                    contrib_fixas=contrib_fixas,
                    lo=lo,
                    hi=hi,
                )
                continue

            idx  = NUTRIENTES_ORDEM.index(nutriente)
            coef = matriz_M_sub[:, idx]           # % da MS por ingrediente
            fixa = float(contrib_fixas[idx])       # contribuição travada

            cls._adicionar_restricoes_limite(
                constraints=constraints,
                coef=coef,
                fixa=fixa,
                lo=lo,
                hi=hi,
            )

        bounds = Bounds(
            lb=[b[0] for b in bounds_sub],
            ub=[b[1] for b in bounds_sub],
        )

        # Ponto inicial: x_alvo projetado para satisfazer a soma
        x0 = cls._projetar_soma(x_alvo_sub.copy(), soma_alvo, bounds_sub)

        resultado = minimize(
            objetivo,
            x0=x0,
            jac=grad_objetivo,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": cls.SLSQP_FTOL, "maxiter": cls.SLSQP_MAXITER},
        )

        if resultado.success:
            fracoes = np.clip(resultado.x, 0.0, 1.0)
            return ResultadoDistribuicao(
                fracoes=fracoes,
                convergiu=True,
                mensagem=f"SLSQP convergiu em {resultado.nit} iterações.",
            )

        # Fallback: nnls sobre x_alvo, normalizado para soma_alvo
        fracoes_fallback = cls._fallback_nnls(
            matriz_M_sub, requisitos, contrib_fixas, soma_alvo, bounds_sub
        )
        return ResultadoDistribuicao(
            fracoes=fracoes_fallback,
            convergiu=False,
            mensagem=(
                f"SLSQP não convergiu ({resultado.message}). "
                "Usando nnls como fallback — alertas indicarão restrições violadas."
            ),
        )

    @staticmethod
    def _adicionar_restricoes_limite(
        constraints: list[dict],
        coef: np.ndarray,
        fixa: float,
        lo: float | None,
        hi: float | None,
    ) -> None:
        if lo is not None:
            rhs_lo = lo - fixa
            constraints.append({
                "type": "ineq",
                "fun": lambda x, c=coef, r=rhs_lo: float(c @ x) - r,
                "jac": lambda x, c=coef: c,
            })
        if hi is not None:
            rhs_hi = hi - fixa
            constraints.append({
                "type": "ineq",
                "fun": lambda x, c=coef, r=rhs_hi: r - float(c @ x),
                "jac": lambda x, c=coef: -c,
            })

    @staticmethod
    def _adicionar_restricoes_relacao_ca_p(
        constraints: list[dict],
        matriz_M_sub: np.ndarray,
        contrib_fixas: np.ndarray,
        lo: float | None,
        hi: float | None,
    ) -> None:
        idx_ca = indice_de(Nutriente.CA)
        idx_p = indice_de(Nutriente.P)

        coef_ca = matriz_M_sub[:, idx_ca]
        coef_p = matriz_M_sub[:, idx_p]
        fixa_ca = float(contrib_fixas[idx_ca])
        fixa_p = float(contrib_fixas[idx_p])

        if lo is not None:
            coef = coef_ca - (lo * coef_p)
            fixa = fixa_ca - (lo * fixa_p)
            constraints.append({
                "type": "ineq",
                "fun": lambda x, c=coef, f=fixa: float(c @ x) + f,
                "jac": lambda x, c=coef: c,
            })

        if hi is not None:
            coef = coef_ca - (hi * coef_p)
            fixa = fixa_ca - (hi * fixa_p)
            constraints.append({
                "type": "ineq",
                "fun": lambda x, c=coef, f=fixa: -(float(c @ x) + f),
                "jac": lambda x, c=coef: -c,
            })

    @staticmethod
    def _fallback_nnls(
        matriz_M_sub: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
        contrib_fixas: np.ndarray,
        soma_alvo: float,
        bounds_sub: list[tuple[float, float]],
    ) -> np.ndarray:
        """
        Aproximação via nnls: encontra x >= 0 que minimiza
        ‖A x - b‖² onde A são os coeficientes nutricionais e
        b são os limites mínimos, depois normaliza para soma_alvo.

        Não garante satisfação das restrições — serve apenas para
        fornecer uma solução "de menor violação" quando SLSQP falha.
        """
        n = matriz_M_sub.shape[0]
        linhas_A, linhas_b = [], []

        for nutriente, requisito in requisitos.items():
            lo, hi = requisito.limites_lp()

            if nutriente == Nutriente.CA_P:
                idx_ca = indice_de(Nutriente.CA)
                idx_p = indice_de(Nutriente.P)
                coef_ca = matriz_M_sub[:, idx_ca]
                coef_p = matriz_M_sub[:, idx_p]
                fixa_ca = float(contrib_fixas[idx_ca])
                fixa_p = float(contrib_fixas[idx_p])

                if lo is not None:
                    linhas_A.append(coef_ca - (lo * coef_p))
                    linhas_b.append(-(fixa_ca - (lo * fixa_p)))
                if hi is not None:
                    linhas_A.append(-(coef_ca - (hi * coef_p)))
                    linhas_b.append(fixa_ca - (hi * fixa_p))
                continue

            idx  = NUTRIENTES_ORDEM.index(nutriente)
            coef = matriz_M_sub[:, idx]
            fixa = float(contrib_fixas[idx])

            if lo is not None:
                linhas_A.append(coef)
                linhas_b.append(lo - fixa)
            if hi is not None:
                linhas_A.append(-coef)
                linhas_b.append(-(hi - fixa))

        if linhas_A:
            A = np.vstack(linhas_A)
            b = np.array(linhas_b, dtype=float)
            x_nnls, _ = nnls(A, b)
        else:
            x_nnls = np.ones(n, dtype=float)

        # Normalizar para soma_alvo respeitando os bounds
        soma = x_nnls.sum()
        if soma > 1e-9:
            x_norm = x_nnls / soma * soma_alvo
        else:
            x_norm = np.full(n, soma_alvo / n)

        # Clip para bounds
        x_clipped = np.array([
            np.clip(x_norm[i], bounds_sub[i][0], bounds_sub[i][1])
            for i in range(n)
        ])

        # Re-normalizar após clip
        soma_clip = x_clipped.sum()
        if soma_clip > 1e-9:
            x_clipped = x_clipped / soma_clip * soma_alvo

        return x_clipped

    @staticmethod
    def _x_alvo_heuristico(
        configuracoes: list[ConfiguracaoIngrediente],
        percentual_volumoso: float,
    ) -> np.ndarray:
        """
        Distribuição-alvo heurística:
        - Volumosos dividem `percentual_volumoso` uniformemente.
        - Concentrados dividem `1 - percentual_volumoso` uniformemente.
        - Se só existir uma classe, distribui uniformemente entre todos.
        """
        n = len(configuracoes)
        idx_vol  = [i for i, c in enumerate(configuracoes) if c.classificacao == "VOLUMOSO"]
        idx_conc = [i for i, c in enumerate(configuracoes) if c.classificacao != "VOLUMOSO"]

        x = np.zeros(n, dtype=float)

        if idx_vol and idx_conc:
            for i in idx_vol:
                x[i] = percentual_volumoso / len(idx_vol)
            for i in idx_conc:
                x[i] = (1.0 - percentual_volumoso) / len(idx_conc)
        else:
            # Só uma classe: distribui uniformemente
            x[:] = 1.0 / n

        return x

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
        # Clip para bounds primeiro
        x = np.array([
            np.clip(x[i], bounds[i][0], bounds[i][1])
            for i in range(len(x))
        ])
        soma = x.sum()
        if soma < 1e-9:
            n = len(x)
            x = np.array([soma_alvo / n] * n)
            return x
        return x / soma * soma_alvo
