"""
Serviço principal de formulação.

Fluxo:
  1. Valida lote e permissão
  2. Busca exigência NRC mais próxima
  3. Monta restrições nutricionais
  4. Busca ingredientes disponíveis
  5. Resolve via Simplex (x em frações 0-1)
  6. Converte frações → kg MS/dia → kg MN/dia → kg nutriente/dia → custo/dia
  7. Persiste Formulacao + IngredienteFormulacao + MotorOtimizacao + Recomendacao
"""
import numpy as np
from django.db import transaction
from django.db.models import Q

from exigencia_nrc.models import ExigenciaNRC
from ingrediente.models import Ingrediente
from lote.models import Lote, FASES_COM_PARTO_E_DIAS

from .restriction_builder import RestrictionBuilder
from ..solvers.linear_solver import LinearSolver, ProblemaInviavelError
from ..models import (
    Formulacao, IngredienteFormulacao, MotorOtimizacao, Recomendacao,
)


class FormulacaoService:

    def __init__(self):
        self.solver = LinearSolver()
        self.rb     = RestrictionBuilder()

    def formular(self, usuario, lote_id, titulo, objetivo,
                 observacoes='', ingredientes_selecionados=None):
        """
        Executa a formulação completa.

        Args:
            usuario:                  instância de Usuario
            lote_id (int):            PK do lote
            titulo (str):             nome da formulação
            objetivo (str):           'CUSTO' | 'PB' | 'FDN'
            observacoes (str):        campo livre
            ingredientes_selecionados (list[int] | None):
                IDs dos ingredientes a usar; None = todos disponíveis

        Returns:
            tuple(Formulacao, MotorOtimizacao, list[Recomendacao])
        """
        # ── 1. Lote ───────────────────────────────────────────────────
        try:
            lote = Lote.objects.get(pk=lote_id)
        except Lote.DoesNotExist:
            raise ValueError(f"Lote {lote_id} não encontrado.")

        if lote.propriedade.usuario != usuario and not getattr(usuario, 'is_staff', False):
            raise PermissionError("Sem permissão para formular este lote.")

        # ── 2. Exigência NRC ──────────────────────────────────────────
        exigencia = self._buscar_exigencia(lote)
        if not exigencia:
            raise ValueError("Nenhuma exigência NRC encontrada para este lote.")

        # ── 3. Restrições nutricionais ────────────────────────────────
        restricoes = self.rb.build_restricoes(exigencia)
        ok, msg    = self.rb.validar_restricoes(restricoes)
        if not ok:
            raise ValueError(f"Restrições inválidas: {msg}")

        # ── 4. Ingredientes ───────────────────────────────────────────
        ingredientes = self._buscar_ingredientes(usuario, ingredientes_selecionados)
        if not ingredientes:
            raise ValueError("Nenhum ingrediente disponível para esta formulação.")

        # ── 5. CMS de referência (kg/dia) ─────────────────────────────
        cms_kg = self._calcular_cms(lote, exigencia)

        # ── 6. Resolver ───────────────────────────────────────────────
        problema = {
            'ingredientes': ingredientes,
            'restricoes':   restricoes,
            'objetivo':     objetivo,
        }

        try:
            solucao       = self.solver.solve(problema)
            status_solver = 'sucesso'
            motivo        = None
        except ProblemaInviavelError as e:
            status_solver = 'inviavel'
            motivo        = str(e)
            solucao       = None

        # ── 7. Persistir ──────────────────────────────────────────────
        with transaction.atomic():
            formulacao = Formulacao.objects.create(
                lote=lote,
                usuario=usuario,
                exigencia=exigencia,
                titulo=titulo,
                objetivo_otimizacao=objetivo,
                observacoes=observacoes,
            )

            motor = MotorOtimizacao.objects.create(
                formulacao=formulacao,
                objetivo=objetivo,
                status=status_solver,
                motivo_inviabilidade=motivo,
                custo_otimizado=solucao['custo'] if solucao else None,
                restricoes_aplicadas=restricoes,
                resultado_simplex=(
                    {str(k): round(v, 6) for k, v in solucao['x'].items()}
                    if solucao else {}
                ),
            )

            if solucao is None:
                return formulacao, motor, []

            # ── 8. Calcular kg/dia e persistir IngredienteFormulacao ──
            recomendacoes = self._salvar_ingredientes_e_totais(
                formulacao, lote, ingredientes, solucao, cms_kg, objetivo
            )

        return formulacao, motor, recomendacoes

    # ──────────────────────────────────────────────────────────────────
    # Helpers privados
    # ──────────────────────────────────────────────────────────────────

    def _salvar_ingredientes_e_totais(self, formulacao, lote, ingredientes,
                                       solucao, cms_kg, objetivo):
        """
        Converte frações x[i] → kg MS → kg MN → kg nutriente → custo.
        Atualiza os totais na Formulacao e persiste IngredienteFormulacao.
        Retorna lista de Recomendacao.
        """
        x       = solucao['x']
        ing_map = {ing.id: ing for ing in ingredientes}

        vol_ms   = 0.0
        conc_ms  = 0.0
        total_mn = 0.0
        total_custo = 0.0

        for ing_id, fracao in x.items():
            if fracao < 1e-4:
                continue
            ing = ing_map.get(ing_id)
            if ing is None:
                continue

            ms_pct    = fracao * 100
            ms_kg_ing = fracao * cms_kg
            # MN = MS / (MS%/100) – converte kg de MS para kg de matéria natural
            ms_frac   = ing.ms / 100.0 if ing.ms and ing.ms > 0 else 1.0
            mn_kg_ing = ms_kg_ing / ms_frac

            pb_kg_ing  = ms_kg_ing * ing.pb  / 100
            ndt_kg_ing = ms_kg_ing * ing.ndt / 100
            fdn_kg_ing = ms_kg_ing * ing.fdn / 100
            ee_kg_ing  = ms_kg_ing * ing.ee  / 100
            ca_kg_ing  = ms_kg_ing * ing.ca  / 100
            p_kg_ing   = ms_kg_ing * ing.p   / 100
            custo_ing  = mn_kg_ing * ing.custo_kg

            IngredienteFormulacao.objects.create(
                formulacao=formulacao,
                ingrediente=ing,
                ms_porcent=round(ms_pct,    2),
                ms_kg     =round(ms_kg_ing, 4),
                mn_kg     =round(mn_kg_ing, 4),
                pb_kg     =round(pb_kg_ing, 4),
                ndt_kg    =round(ndt_kg_ing,4),
                fdn_kg    =round(fdn_kg_ing,4),
                ee_kg     =round(ee_kg_ing, 4),
                ca_kg     =round(ca_kg_ing, 4),
                p_kg      =round(p_kg_ing,  4),
                custo_dia =round(custo_ing, 4),
            )

            if ing.classificacao == 'volumoso':
                vol_ms  += ms_pct
            else:
                conc_ms += ms_pct

            total_mn    += mn_kg_ing
            total_custo += custo_ing

        # Atualizar totais na Formulacao
        formulacao.vol_ms_percent   = round(vol_ms,   2)
        formulacao.conc_ms_percent  = round(conc_ms,  2)
        formulacao.mistura_conc     = round(conc_ms / 100 * cms_kg, 4)
        formulacao.rs_kg_mn_total   = round(total_mn, 4)
        formulacao.custo_animal_dia = round(total_custo, 4)
        formulacao.custo_lote_dia   = round(total_custo * lote.num_animais, 4)
        formulacao.save(update_fields=[
            'vol_ms_percent', 'conc_ms_percent', 'mistura_conc',
            'rs_kg_mn_total', 'custo_animal_dia', 'custo_lote_dia',
        ])

        return self._gerar_recomendacoes(formulacao, ingredientes, x, objetivo)

    def _buscar_exigencia(self, lote):
        qs = ExigenciaNRC.objects.filter(
            categoria=lote.categoria, fase=lote.fase
        )
        if lote.fase in FASES_COM_PARTO_E_DIAS and lote.tipo_parto:
            qs = qs.filter(tipo_parto=lote.tipo_parto)
        if not qs.exists():
            return None
        best = min(qs, key=lambda e: abs((e.pv_kg or 0) - lote.peso_vivo))
        mesmo_pv = [e for e in qs if e.pv_kg == best.pv_kg]
        if len(mesmo_pv) > 1 and lote.gmd_esperado:
            best = min(mesmo_pv, key=lambda e: abs((e.gmd_kg or 0) - lote.gmd_esperado))
        return best

    def _buscar_ingredientes(self, usuario, selecionados):
        qs = Ingrediente.objects.filter(
            Q(fonte_valadares=True) | Q(usuario=usuario)
        )
        if selecionados:
            qs = qs.filter(id__in=selecionados)
        return list(qs)

    def _calcular_cms(self, lote, exigencia):
        """CMS em kg/dia. Prioriza valor da tabela NRC; fallback: PV × %PV."""
        if exigencia.cms_kg and exigencia.cms_kg > 0:
            return float(exigencia.cms_kg)
        pv_pct = (
            lote.pv_percentual
            or (exigencia.pv_percentual if exigencia.pv_percentual else 3.5)
        )
        return round(lote.peso_vivo * pv_pct / 100, 4)

    def _gerar_recomendacoes(self, formulacao, ingredientes, x_atual, objetivo):
        """
        Para cada ingrediente não usado, calcula:
          - ingrediente usado mais próximo (distância euclidiana nutricional)
          - delta de custo, PB e NDT
          - score pelo objetivo

        Persiste top 5 por score.
        """
        ing_map  = {ing.id: ing for ing in ingredientes}
        usados   = {iid: ing_map[iid] for iid, fr in x_atual.items()
                    if fr >= 1e-4 and iid in ing_map}
        candidatos = [ing for ing in ingredientes if x_atual.get(ing.id, 0) < 1e-4]

        if not usados or not candidatos:
            return []

        recs_data = []
        for cand in candidatos:
            vec_c = np.array([cand.pb, cand.ndt, cand.fdn, cand.ee, cand.ca, cand.p])
            melhor_dist = None
            melhor_sub  = None
            for used_ing in usados.values():
                vec_u = np.array([used_ing.pb, used_ing.ndt, used_ing.fdn,
                                  used_ing.ee, used_ing.ca, used_ing.p])
                dist = float(np.linalg.norm(vec_c - vec_u))
                if melhor_dist is None or dist < melhor_dist:
                    melhor_dist = dist
                    melhor_sub  = used_ing

            if melhor_sub is None:
                continue

            delta_custo = cand.custo_kg - melhor_sub.custo_kg
            delta_pb    = cand.pb  - melhor_sub.pb
            delta_ndt   = cand.ndt - melhor_sub.ndt

            if objetivo == 'CUSTO':
                score = -delta_custo
            elif objetivo == 'PB':
                score = delta_pb
            else:  # FDN
                score = -(cand.fdn - melhor_sub.fdn)

            recs_data.append((score, cand, melhor_sub, delta_custo, delta_pb, delta_ndt, melhor_dist))

        # Ordenar por score descendente, pegar top 5
        recs_data.sort(key=lambda t: t[0], reverse=True)
        recomendacoes = []
        for score, cand, sub, dc, dpb, dndt, dist in recs_data[:5]:
            r = Recomendacao.objects.create(
                formulacao=formulacao,
                ingrediente_sugerido=cand,
                ingrediente_substituido=sub,
                objetivo=objetivo,
                score=round(score, 4),
                delta_custo=round(dc,   4),
                delta_pb   =round(dpb,  4),
                delta_ndt  =round(dndt, 4),
                distancia_euclidiana=round(dist, 4),
            )
            recomendacoes.append(r)

        return recomendacoes
