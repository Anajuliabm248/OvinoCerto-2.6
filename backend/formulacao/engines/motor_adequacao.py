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
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import Bounds, minimize

from formulacao.domain.nutrientes import NUTRIENTES_ORDEM, Nutriente, indice_de
from formulacao.domain.participacao import ParticipacaoVetor
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
    tipo: str = "OUTRO"         # ENERGETICO | PROTEICO | MINERAL | ADITIVOS | ...

    def __post_init__(self) -> None:
        object.__setattr__(self, "classificacao", self.classificacao.upper())
        object.__setattr__(self, "tipo", self.tipo.upper())
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
                 False indica fallback numérico; as regras estruturais
                 continuam válidas e os alertas reportam desvios nutricionais.
    mensagem   : descrição do status do solver para log/auditoria.
    """
    fracoes: np.ndarray = field(repr=False)
    convergiu: bool
    mensagem: str


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
        cls._validar_dimensoes(matriz_M, n)

        alvo_vol = cls._normalizar_percentual_volumoso(
            percentual_alvo_volumoso
            if percentual_alvo_volumoso is not None
            else cls.PERCENTUAL_ALVO_VOLUMOSO
        )

        x_alvo = cls._x_alvo_heuristico(configuracoes, alvo_vol)
        bounds = cls._bounds_geracao(
            configuracoes=configuracoes,
            soma_total=1.0,
            percentual_volumoso=alvo_vol,
        )
        mascara_volumoso = cls._mascara_volumoso(configuracoes)

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
        if reiniciar_livres and percentual_alvo_volumoso is not None:
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

        if reiniciar_livres:
            x_alvo_livres = cls._x_alvo_heuristico(
                cfg_livres,
                percentual_volumoso_livre,
            )
            x_alvo_livres = x_alvo_livres * espaco_livre
        elif soma_livres_atual > 1e-9:
            x_alvo_livres = fracoes_livres_atuais / soma_livres_atual * espaco_livre
        else:
            x_alvo_livres = cls._x_alvo_heuristico(cfg_livres, alvo_vol)
            x_alvo_livres = x_alvo_livres * espaco_livre

        bounds_geracao = None
        if reiniciar_livres:
            bounds_geracao = cls._bounds_geracao(
                configuracoes=cfg_livres,
                soma_total=espaco_livre,
                percentual_volumoso=percentual_volumoso_livre,
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
        mascara_volumoso_sub: np.ndarray | None = None,
        soma_volumoso_alvo: float | None = None,
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
            desvio_distribuicao = float(diff @ diff)
            desvio_nutricional = cls._penalidade_nutricional(
                x=x,
                matriz_M_sub=matriz_M_sub,
                requisitos=requisitos,
                contrib_fixas=contrib_fixas,
            )
            return (
                desvio_distribuicao
                + cls.PESO_ADEQUACAO_NUTRICIONAL * desvio_nutricional
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
                    "iterações; desvios nutricionais são informados por alertas."
                ),
            )

        return ResultadoDistribuicao(
            fracoes=x0,
            convergiu=False,
            mensagem=(
                f"SLSQP não convergiu ({resultado.message}). "
                "Mantida a distribuição-alvo projetada dentro de todas as regras estruturais."
            ),
        )

    @staticmethod
    def _penalidade_nutricional(
        x: np.ndarray,
        matriz_M_sub: np.ndarray,
        requisitos: dict[Nutriente, RequisitoNutriente],
        contrib_fixas: np.ndarray,
    ) -> float:
        penalidade = 0.0
        totais = x @ matriz_M_sub + contrib_fixas

        for nutriente, requisito in requisitos.items():
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
    def _x_alvo_heuristico(
        cls,
        configuracoes: list[ConfiguracaoIngrediente],
        percentual_volumoso: float,
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
    def _mascara_volumoso(configuracoes: list[ConfiguracaoIngrediente]) -> np.ndarray:
        return np.array([c.classificacao == "VOLUMOSO" for c in configuracoes], dtype=bool)

    @classmethod
    def _bounds_geracao(
        cls,
        configuracoes: list[ConfiguracaoIngrediente],
        soma_total: float,
        percentual_volumoso: float | None,
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
        if abs(float(x.sum()) - soma_alvo) > 1e-10:
            raise RuntimeError("Falha interna ao projetar participações para a soma alvo.")
        return x
