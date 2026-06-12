"""
Solver linear usando scipy.optimize.linprog (HiGHS).

Variáveis x[i]: fração de cada ingrediente na MS total.
  - x[i] ∈ [0, 1]
  - Σ x[i] = 1  (restrição de igualdade sempre incluída)

Nutrientes como média ponderada:
  nutriente_total = Σ( x[i] * nutriente[i] )   → resultado em %

"""
import time
import numpy as np
from scipy.optimize import linprog


class ProblemaInviavelError(Exception):
    """Levantada quando o problema não tem solução viável."""
    pass


# Limites máximos de inclusão na MS para ingredientes especiais
_LIMITES_ESPECIAIS = {
    'ureia':                0.01,
    'bicarbonato de sódio': 0.01,
    'bicarbonato de sodio': 0.01,
    'cloreto de amônio':    0.005,
    'cloreto de amonio':    0.005,
}


class LinearSolver:
    """Solver de formulação de rações via programação linear (Simplex/HiGHS)."""

    def solve(self, problema):
        """
        Resolve o problema de formulação.

        Args:
            problema (dict):
                - ingredientes (list[Ingrediente])
                - restricoes   (list[{nutriente, operador, valor}])
                - objetivo     (str): 'CUSTO' | 'PB' | 'FDN'

        Returns:
            dict: x (frações 0-1), nutrientes (%), custo (R$/kg MS), tempo_ms

        Raises:
            ProblemaInviavelError
        """
        inicio = time.time()

        ingredientes = problema['ingredientes']
        restricoes   = problema['restricoes']
        objetivo     = problema['objetivo']
        n            = len(ingredientes)

        if n == 0:
            raise ProblemaInviavelError("Nenhum ingrediente disponível.")

        # ── 1. Vetor objetivo c  (minimizar c·x) ──────────────────────
        c = self._build_objective(ingredientes, objetivo)

        # ── 2. Desigualdades: A_ub·x ≤ b_ub ───────────────────────────
        A_ub, b_ub = self._build_ineq(ingredientes, restricoes)

        # ── 3. Igualdades: A_eq·x = b_eq ──────────────────────────────
        #    Sempre inclui Σxᵢ = 1  +  qualquer restrição com operador '='
        A_eq, b_eq = self._build_eq(n, ingredientes, restricoes)

        # ── 4. Bounds por variável ─────────────────────────────────────
        bounds = self._build_bounds(ingredientes)

        # ── 5. Resolver ────────────────────────────────────────────────
        result = linprog(
            c,
            A_ub=A_ub if A_ub.size > 0 else None,
            b_ub=b_ub if b_ub.size > 0 else None,
            A_eq=A_eq,
            b_eq=b_eq,
            bounds=bounds,
            method='highs',
            options={'disp': False, 'presolve': True},
        )

        if not result.success:
            raise ProblemaInviavelError(
                f"Problema inviável: {result.message}. "
                "Verifique se há ingredientes suficientes para atender as exigências nutricionais."
            )

        # ── 6. Pós-processamento ───────────────────────────────────────
        x_raw = np.maximum(result.x, 0.0)   # zerar negativos numéricos
        soma  = x_raw.sum()
        if soma < 1e-9:
            raise ProblemaInviavelError("Solução trivial (todas as proporções são zero).")
        x_raw /= soma  # normalizar para Σ = 1 exato

        ids    = [ing.id for ing in ingredientes]
        x_dict = {ids[i]: float(x_raw[i]) for i in range(n)}

        # ── 7. Nutrientes obtidos (% da MS) ────────────────────────────
        nutrientes = self._calc_nutrientes(x_dict, ingredientes)

        # ── 8. Custo total (R$/kg MS) ───────────────────────────────────
        ing_map    = {ing.id: ing for ing in ingredientes}
        custo_ms   = sum(
            x_dict[iid] * ing_map[iid].custo_kg for iid in x_dict
        )

        return {
            'x':          x_dict,           # frações 0-1 por id
            'nutrientes': nutrientes,        # {nutriente: valor_%}
            'custo':      round(custo_ms, 4),
            'tempo_ms':   (time.time() - inicio) * 1000,
        }

    # ──────────────────────────────────────────────────────────────────
    # Builders privados
    # ──────────────────────────────────────────────────────────────────

    def _build_objective(self, ingredientes, objetivo):
        n = len(ingredientes)
        c = np.zeros(n)
        for i, ing in enumerate(ingredientes):
            if objetivo == 'CUSTO':
                c[i] = ing.custo_kg
            elif objetivo == 'PB':
                c[i] = -ing.pb          # maximizar PB → minimizar −PB
            elif objetivo == 'FDN':
                c[i] = ing.fdn          # minimizar FDN diretamente
            else:
                c[i] = ing.custo_kg     # fallback: custo
        return c

    def _build_ineq(self, ingredientes, restricoes):
        """
        Restrições '>=' e '<=' convertidas para A_ub·x ≤ b_ub.

        '>=' (ex: PB >= 14%):  -Σ(pbᵢ·xᵢ) ≤ -14  →  Σ(pbᵢ·xᵢ) ≥ 14
        '<=' (ex: FDN <= 60%):  Σ(fdnᵢ·xᵢ) ≤ 60
        """
        rows, rhs = [], []
        for r in restricoes:
            if r['operador'] not in ('>=', '<='):
                continue
            linha = np.array([
                getattr(ing, r['nutriente'].lower(), 0.0)
                for ing in ingredientes
            ], dtype=float)
            if r['operador'] == '>=':
                rows.append(-linha)
                rhs.append(-float(r['valor']))
            else:
                rows.append(linha)
                rhs.append(float(r['valor']))

        if not rows:
            return np.empty((0, len(ingredientes))), np.empty(0)
        return np.array(rows), np.array(rhs)

    def _build_eq(self, n, ingredientes, restricoes):
        """
        Restrições de igualdade
        garante que as proporções somem 1 -> 100%
        """
        rows = [np.ones(n, dtype=float)]
        rhs  = [1.0]

        for r in restricoes:
            if r['operador'] != '=': # caso operador seja de igualdade (ainda não utilizado)
                continue
            linha = np.array([
                getattr(ing, r['nutriente'].lower(), 0.0)
                for ing in ingredientes
            ], dtype=float)
            rows.append(linha)
            rhs.append(float(r['valor']))

        return np.array(rows), np.array(rhs)

    def _build_bounds(self, ingredientes):
        """
        aplica limites de inclusão de alguns ingredientes:
        'ureia':                0.01,
        'bicarbonato de sódio': 0.01,
        'bicarbonato de sodio': 0.01,
        'cloreto de amônio':    0.005,
        'cloreto de amonio':    0.005,
        """
        bounds = []
        for ing in ingredientes:
            nome_lower = ing.nome.lower().strip()
            ub = 1.0
            for chave, limite in _LIMITES_ESPECIAIS.items():
                if chave in nome_lower:
                    ub = limite
                    break
            bounds.append((0.0, ub))
        return bounds

    def _calc_nutrientes(self, x_dict, ingredientes):
        """
        Calcula a média ponderada de cada nutriente na dieta (em %).
        nutriente_dieta = Σ( x[i] * nutriente[i] )
        """
        nutrientes = {}
        for nut in ('PB', 'NDT', 'FDN', 'EE', 'Ca', 'P'):
            attr = nut.lower()
            total = sum(
                x_dict.get(ing.id, 0.0) * getattr(ing, attr, 0.0)
                for ing in ingredientes
            )
            nutrientes[nut] = round(total, 4)
        return nutrientes
