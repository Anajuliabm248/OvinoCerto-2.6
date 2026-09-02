"""
Repository - IngredienteFormulacao.

ÚNICO ponto do sistema onde ocorre a conversão de escala:
  DB  (ms_porcent 0-100)  ←→  Domínio (fracao 0-1)

Qualquer leitura do banco para o domínio divide por 100.
Qualquer escrita do domínio para o banco multiplica por 100.
Nenhuma outra camada (domain, engine, service, serializer) faz essa
conversão — isso é o que previne o bug de escala descrito na seção 2
do documento de arquitetura.
"""

from __future__ import annotations

import numpy as np
from django.db import transaction
from django.db.models import Sum

from ingrediente.models import PrecoIngredienteUsuario
from formulacao.domain.nutrientes import NUTRIENTES_ORDEM, Nutriente
from formulacao.domain.participacao import OrigemParticipacao, ParticipacaoVetor
from formulacao.domain.vetor_nutricional import VetorNutricional
from formulacao.engines.motor_recalculo import SaidaRecalculo
from formulacao.engines.motor_custo import SaidaCusto
from formulacao.engines.motor_dados_dieta import LinhaDadosDietaEntrada
from formulacao.models import Formulacao, IngredienteFormulacao, OrigemParticipacaoChoices


# Mapeamento entre o enum de domínio e o TextChoices do model.
# Mantidos separados para não criar dependência Django → domínio.
_ORIGEM_DOMINIO_PARA_DB: dict[OrigemParticipacao, str] = {
    OrigemParticipacao.CALCULADA:      OrigemParticipacaoChoices.CALCULADA,
    OrigemParticipacao.MANUAL_TRAVADA: OrigemParticipacaoChoices.MANUAL_TRAVADA,
}
_ORIGEM_DB_PARA_DOMINIO: dict[str, OrigemParticipacao] = {
    v: k for k, v in _ORIGEM_DOMINIO_PARA_DB.items()
}


class IngredienteFormulacaoRepository:
    """Mantém a ordem dos ingredientes ao traduzir ORM, vetores e resultados."""

    
    # Leitura: DB → Domínio
    

    @staticmethod
    def get_participacao(formulacao_id: int) -> ParticipacaoVetor:
        """
        Carrega os IngredienteFormulacao de uma formulação e constrói
        um ParticipacaoVetor com fracoes em 0-1.

        CONVERSÃO: ms_porcent (0-100) / 100 → fracao (0-1).
        """
        qs = (
            IngredienteFormulacao.objects
            .filter(formulacao_id=formulacao_id)
            .order_by("id")
            .values("id", "ms_porcent", "origem_participacao")
        )
        registros = list(qs)
        if not registros:
            return ParticipacaoVetor(
                ids_ingredientes=(),
                fracoes=np.array([], dtype=float),
                origens=(),
            )

        ids     = tuple(r["id"] for r in registros)
        fracoes = np.array([r["ms_porcent"] / 100.0 for r in registros], dtype=float)
        origens = tuple(
            _ORIGEM_DB_PARA_DOMINIO[r["origem_participacao"]] for r in registros
        )
        return ParticipacaoVetor(
            ids_ingredientes=ids,
            fracoes=fracoes,
            origens=origens,
        )

    @staticmethod
    def get_percentual_volumoso_aplicado(formulacao_id: int) -> float:
        """Soma volumosos no banco 0-100 e devolve a fracao de dominio 0-1."""
        soma_percentual = (
            IngredienteFormulacao.objects
            .filter(
                formulacao_id=formulacao_id,
                ingrediente__classificacao__iexact="volumoso",
            )
            .aggregate(soma=Sum("ms_porcent"))["soma"]
            or 0.0
        )
        return float(soma_percentual) / 100.0

    @staticmethod
    def get_vetores_nutricionais(formulacao_id: int) -> list[VetorNutricional]:
        """
        Retorna um VetorNutricional por ingrediente, na mesma ordem de
        get_participacao() — essencial para que os índices da
        ParticipacaoVetor e da matriz M do MotorRecalculo estejam
        alinhados.

        Valores do Ingrediente (pb, ndt, fdn, ee, ca, p) já estão em
        % da MS no banco — sem conversão necessária.
        """
        qs = (
            IngredienteFormulacao.objects
            .filter(formulacao_id=formulacao_id)
            .order_by("id")
            .select_related("ingrediente")
        )
        vetores = []
        for ing_form in qs:
            ing = ing_form.ingrediente
            if ing is None:
                # Ingrediente removido: vetor zerado (snapshot preserva
                # os valores calculados no momento; aqui usamos 0 para
                # não distorcer um recálculo com ingrediente ausente).
                vetores.append(VetorNutricional.zeros())
            else:
                vetores.append(
                    VetorNutricional.from_dict({
                        "PB":  float(ing.pb),
                        "NDT": float(ing.ndt),
                        "FDN": float(ing.fdn),
                        "EE":  float(ing.ee),
                        "CA":  float(ing.ca),
                        "P":   float(ing.p),
                    })
                )
        return vetores

    @staticmethod
    def get_limites_participacao(formulacao_id: int) -> list[dict]:
        """
        Retorna, um item por IngredienteFormulacao (ordenado por id, a
        MESMA ordem de get_participacao()), os metadados necessários
        para avaliar o limite máximo de participação:

          [{"ing_form_id": int, "nome": str, "limite_max_fracao": float | None}, ...]

        limite_max_fracao vem de Ingrediente.limite_max_participacao
        (armazenado em % 0-100) convertido para fração 0-1. É None
        quando o ingrediente não tem limite configurado, ou quando o
        ingrediente foi removido do catálogo (SET_NULL).
        """
        qs = (
            IngredienteFormulacao.objects
            .filter(formulacao_id=formulacao_id)
            .order_by("id")
            .select_related("ingrediente")
        )
        resultado = []
        for ing_form in qs:
            ing = ing_form.ingrediente
            if ing is None or ing.limite_max_participacao is None:
                limite_fracao = None
            else:
                limite_fracao = ing.limite_max_participacao / 100.0
            resultado.append({
                "ing_form_id":       ing_form.id,
                "nome":              ing.nome if ing else "(removido)",
                "limite_max_fracao": limite_fracao,
            })
        return resultado

    @staticmethod
    def get_nomes_e_ids(formulacao_id: int) -> tuple[list[str], list[int | None]]:
        """
        Retorna (nomes, ingrediente_ids), na MESMA ordem de
        get_participacao()/get_dados_custo() — usado pelo
        MotorViabilidade para rotular cada linha do Quadro 6.

        Ingrediente removido (SET_NULL): nome="(removido)", id=None.
        """
        qs = (
            IngredienteFormulacao.objects
            .filter(formulacao_id=formulacao_id)
            .order_by("id")
            .select_related("ingrediente")
        )
        nomes: list[str] = []
        ids: list[int | None] = []
        for ing_form in qs:
            ing = ing_form.ingrediente
            nomes.append(ing.nome if ing else "(removido)")
            ids.append(ing.id if ing else None)
        return nomes, ids

    @staticmethod
    def get_dados_custo(formulacao_id: int) -> tuple[np.ndarray, np.ndarray]:
        """
        Retorna (custos_kg_mn, ms_percentuais), ambos na MESMA ordem
        de get_participacao() — essencial para o alinhamento posicional
        que o MotorCusto espera em EntradaCusto.

        Resolução de precedência do preço (ÚNICO ponto do sistema onde
        isso acontece):
          1. IngredienteFormulacao.custo_kg_mn_override, se definido
             (usuário escolheu "atualizar só nesta receita").
          2. PrecoIngredienteUsuario do DONO da formulação para este
             ingrediente — o "banco de preços regional" do usuário
             (requisito #1 da Fase 2). NÃO usa Ingrediente.custo_kg:
             esse campo é compartilhado por todos os usuários do
             catálogo Valadares, então gravar preço ali vazaria entre
             contas diferentes (ver docstring de PrecoIngredienteUsuario
             em ingrediente/models.py).
          3. 0.0 — tratado como "sem preço informado" pelo MotorCusto
             (não gera ZeroDivisionError, apenas custo 0 e a flag
             tem_ingrediente_sem_preco=True na saída).

        ms_percentuais vem de Ingrediente.ms, usado pelo MotorCusto para
        converter custo por kg de MN em custo por kg de MS. Ingrediente
        removido (SET_NULL) entra com custo 0.0 e ms 0.0 — mesmo
        tratamento dado em get_vetores_nutricionais.
        """
        usuario_id = (
            Formulacao.objects
            .values_list("usuario_id", flat=True)
            .get(id=formulacao_id)
        )

        linhas = list(
            IngredienteFormulacao.objects
            .filter(formulacao_id=formulacao_id)
            .order_by("id")
            .select_related("ingrediente")
        )

        ids_ingredientes = [l.ingrediente_id for l in linhas if l.ingrediente_id]
        precos_usuario = dict(
            PrecoIngredienteUsuario.objects
            .filter(usuario_id=usuario_id, ingrediente_id__in=ids_ingredientes)
            .values_list("ingrediente_id", "preco_kg_mn")
        )

        custos: list[float] = []
        ms_percentuais: list[float] = []
        for ing_form in linhas:
            ing = ing_form.ingrediente
            if ing_form.custo_kg_mn_override is not None:
                custo = float(ing_form.custo_kg_mn_override)
            elif ing is not None and ing.id in precos_usuario:
                custo = float(precos_usuario[ing.id])
            else:
                custo = 0.0
            custos.append(custo)
            ms_percentuais.append(float(ing.ms) if ing is not None else 0.0)

        return (
            np.array(custos, dtype=float),
            np.array(ms_percentuais, dtype=float),
        )

    @staticmethod
    def get_linhas_dados_dieta(
        formulacao_id: int,
    ) -> tuple[LinhaDadosDietaEntrada, ...]:
        """Entrega linhas alinhadas e resolve preço sem ocultar ausência."""
        usuario_id = (
            Formulacao.objects
            .values_list("usuario_id", flat=True)
            .get(id=formulacao_id)
        )
        linhas = list(
            IngredienteFormulacao.objects
            .filter(formulacao_id=formulacao_id)
            .select_related("ingrediente")
            .order_by("id")
        )
        ids_ingredientes = [
            linha.ingrediente_id for linha in linhas if linha.ingrediente_id
        ]
        precos_usuario = dict(
            PrecoIngredienteUsuario.objects
            .filter(
                usuario_id=usuario_id,
                ingrediente_id__in=ids_ingredientes,
            )
            .values_list("ingrediente_id", "preco_kg_mn")
        )

        saida = []
        for linha in linhas:
            ingrediente = linha.ingrediente
            if linha.custo_kg_mn_override is not None:
                preco = float(linha.custo_kg_mn_override)
            elif ingrediente is not None and ingrediente.id in precos_usuario:
                preco = float(precos_usuario[ingrediente.id])
            else:
                preco = None
            saida.append(LinhaDadosDietaEntrada(
                ing_form_id=linha.id,
                ingrediente_id=linha.ingrediente_id,
                classificacao=(
                    ingrediente.classificacao if ingrediente is not None else ""
                ),
                tipo=ingrediente.tipo if ingrediente is not None else "",
                nome=ingrediente.nome if ingrediente is not None else "(removido)",
                ms_percentual_ingrediente=(
                    float(ingrediente.ms) if ingrediente is not None else None
                ),
                ms_kg_dia=float(linha.ms_kg),
                mn_kg_dia=float(linha.mn_kg),
                participacao_ms_percentual=float(linha.ms_porcent),
                preco_kg_mn=preco,
                custo_dia=float(linha.custo_dia),
                origem_custo=linha.origem_custo,
            ))
        return tuple(saida)

    @staticmethod
    def get_num_animais(formulacao_id: int) -> int:
        """Número de animais do lote associado — usado para custo_lote_dia."""
        return (
            Formulacao.objects
            .select_related("lote")
            .values_list("lote__num_animais", flat=True)
            .get(id=formulacao_id)
        )

    
    # Escrita: Domínio → DB
    

    @staticmethod
    @transaction.atomic
    def salvar_saida_recalculo(
        formulacao_id: int,
        participacao: ParticipacaoVetor,
        saida: SaidaRecalculo,
    ) -> None:
        """
        Persiste os campos calculados pelo MotorRecalculo de volta nos
        registros IngredienteFormulacao correspondentes.

        CONVERSÃO: fracao (0-1) * 100 → ms_porcent (0-100).

        Usa bulk_update para evitar N queries.
        A correspondência entre participacao.ids_ingredientes[i] e
        saida.contribuicoes_kg[i] é posicional — a ordem deve ser a
        mesma produzida por get_participacao() e get_vetores_nutricionais().
        """
        ids = participacao.ids_ingredientes
        if not ids:
            return

        qs = {
            obj.id: obj
            for obj in IngredienteFormulacao.objects.filter(
                id__in=ids, formulacao_id=formulacao_id
            )
        }

        indice = {n: i for i, n in enumerate(NUTRIENTES_ORDEM)}
        ipb  = indice[Nutriente.PB]
        indt = indice[Nutriente.NDT]
        ifdn = indice[Nutriente.FDN]
        iee  = indice[Nutriente.EE]
        ica  = indice[Nutriente.CA]
        ip   = indice[Nutriente.P]

        para_atualizar = []
        for pos, ing_form_id in enumerate(ids):
            obj = qs.get(ing_form_id)
            if obj is None:
                continue

            ms_kg = float(saida.ms_kg_ingredientes[pos])
            ms_porcent_db = float(participacao.fracoes[pos]) * 100.0

            # mn_kg: massa em matéria natural (kg de MN/dia)
            # mn_kg = ms_kg / (ms% do ingrediente / 100)
            # Se ingrediente removido (ms=0), evitamos divisão por zero.
            ing_ms_pct = obj.ingrediente.ms if obj.ingrediente else 0.0
            mn_kg = (ms_kg / (ing_ms_pct / 100.0)) if ing_ms_pct > 0 else 0.0

            obj.ms_porcent = ms_porcent_db
            obj.ms_kg      = ms_kg
            obj.mn_kg      = mn_kg
            obj.pb_kg      = float(saida.contribuicoes_kg[pos, ipb])
            obj.ndt_kg     = float(saida.contribuicoes_kg[pos, indt])
            obj.fdn_kg     = float(saida.contribuicoes_kg[pos, ifdn])
            obj.ee_kg      = float(saida.contribuicoes_kg[pos, iee])
            obj.ca_kg      = float(saida.contribuicoes_kg[pos, ica])
            obj.p_kg       = float(saida.contribuicoes_kg[pos, ip])
            para_atualizar.append(obj)

        if para_atualizar:
            IngredienteFormulacao.objects.bulk_update(
                para_atualizar,
                fields=[
                    "ms_porcent", "ms_kg", "mn_kg",
                    "pb_kg", "ndt_kg", "fdn_kg",
                    "ee_kg", "ca_kg", "p_kg",
                ],
            )

    @staticmethod
    @transaction.atomic
    def salvar_saida_custo(
        formulacao_id: int,
        ids_ingredientes: tuple[int, ...],
        saida: SaidaCusto,
    ) -> None:
        """
        Persiste os campos calculados pelo MotorCusto: custo_dia por
        IngredienteFormulacao + os 4 indicadores-resumo em Formulacao.

        `ids_ingredientes` deve ser EXATAMENTE participacao.ids_ingredientes
        usada para montar a EntradaCusto — a correspondência com
        saida.custo_por_ingrediente_dia é posicional, igual ao padrão de
        salvar_saida_recalculo.
        """
        if ids_ingredientes:
            qs = {
                obj.id: obj
                for obj in IngredienteFormulacao.objects.filter(
                    id__in=ids_ingredientes, formulacao_id=formulacao_id
                )
            }
            para_atualizar = []
            for pos, ing_form_id in enumerate(ids_ingredientes):
                obj = qs.get(ing_form_id)
                if obj is None:
                    continue
                obj.custo_dia = float(saida.custo_por_ingrediente_dia[pos])
                para_atualizar.append(obj)

            if para_atualizar:
                IngredienteFormulacao.objects.bulk_update(
                    para_atualizar, fields=["custo_dia"]
                )

        Formulacao.objects.filter(id=formulacao_id).update(
            custo_mn_kg=saida.custo_mn_kg,
            custo_ms_kg=saida.custo_ms_kg,
            custo_animal_dia=saida.custo_animal_dia,
            custo_lote_dia=saida.custo_lote_dia,
        )

    @staticmethod
    def atualizar_participacao(
        ing_form_id: int,
        fracao: float,
        origem: OrigemParticipacao,
    ) -> None:
        """
        Atualiza ms_porcent e origem_participacao de um único registro.

        Chamado pelo Application Service quando o usuário edita
        manualmente a participação de um ingrediente.

        CONVERSÃO: fracao (0-1) * 100 → ms_porcent (0-100).
        """
        IngredienteFormulacao.objects.filter(id=ing_form_id).update(
            ms_porcent=fracao * 100.0,
            origem_participacao=_ORIGEM_DOMINIO_PARA_DB[origem],
        )

    @staticmethod
    def atualizar_origens_bulk(
        updates: list[tuple[int, OrigemParticipacao]],
    ) -> None:
        """
        Atualiza a origem de múltiplos registros.
        `updates`: lista de (ing_form_id, nova_origem).
        Usado pela redistribuição automática ao gravar novas frações.
        """
        ids_calculadas = [
            id_ for id_, origem in updates
            if origem == OrigemParticipacao.CALCULADA
        ]
        ids_travadas = [
            id_ for id_, origem in updates
            if origem == OrigemParticipacao.MANUAL_TRAVADA
        ]
        if ids_calculadas:
            IngredienteFormulacao.objects.filter(id__in=ids_calculadas).update(
                origem_participacao=OrigemParticipacaoChoices.CALCULADA,
            )
        if ids_travadas:
            IngredienteFormulacao.objects.filter(id__in=ids_travadas).update(
                origem_participacao=OrigemParticipacaoChoices.MANUAL_TRAVADA,
            )
