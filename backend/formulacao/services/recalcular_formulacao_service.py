"""
Application Service - RecalcularFormulacaoService.

Orquestra o pipeline completo de recálculo nutricional E econômico:

  1. Carrega ParticipacaoVetor e VetorNutricional[] via repositórios
  2. Carrega requisitos (dict[Nutriente, RequisitoNutriente]) e cms_kg
  3. Monta EntradaRecalculo
  4. Executa MotorRecalculo.calcular() → SaidaRecalculo
  4b. Carrega dados de custo e executa MotorCusto.calcular() → SaidaCusto
  5. Persiste campos *_kg via IngredienteFormulacaoRepository
  5b. Persiste custo_dia por ingrediente + indicadores-resumo da Formulação
  6. Avalia alertas via MotorAlertas (nutricionais + limite + custo)
  7. Constrói payload do snapshot (inclui bloco "custos")
  8. Persiste SnapshotFormulacao via SnapshotRepository
  9. Faz upsert de alertas via AlertaRepository
  10. Registra EventoFormulacao

Todo o passo 5-10 ocorre dentro de transaction.atomic.
MotorRecalculo (passo 4) e MotorCusto (passo 4b) são executados FORA
da transação — ambos são puros e sem I/O, não precisam de lock.

Custo NÃO influencia adequação nutricional (é um agregado ortogonal,
seção 2.4/19 do documento de arquitetura) — por isso é calculado em
paralelo ao MotorRecalculo, não encadeado a ele. Uma falha ao carregar
dados de custo (ex.: CMS ainda não definido) não deveria impedir o
recálculo nutricional; por isso 4b é best-effort: se os dados de custo
não puderem ser montados, a formulação segue sem indicadores de custo
nesta rodada, sem lançar exceção.

Retorna SaidaRecalculo para que a view possa serializar o resultado
sem precisar re-consultar o banco. SaidaCusto vai dentro do payload do
snapshot — quem precisar dela separadamente usa GET /formulacoes/{id}/custos/.
"""

from __future__ import annotations

from django.db import transaction

from formulacao.domain.nutrientes import NUTRIENTES_ORDEM
from formulacao.engines.motor_alertas import MotorAlertas, ParticipacaoIngredienteLimite
from formulacao.engines.motor_custo import EntradaCusto, MotorCusto, SaidaCusto
from formulacao.engines.motor_recalculo import EntradaRecalculo, MotorRecalculo, SaidaRecalculo
from formulacao.models import Formulacao, TipoEvento
from formulacao.repositories import (
    AlertaRepository,
    EventoRepository,
    ExigenciaRepository,
    IngredienteFormulacaoRepository,
    SnapshotRepository,
)


class RecalcularFormulacaoService:
    """Orquestra adequação, custos, alertas, snapshot e evento em uma transação."""

    @staticmethod
    def executar(
        formulacao_id: int,
        usuario_id: int | None = None,
        motivo: str = "recálculo",
    ) -> SaidaRecalculo:
        """
        Ponto de entrada único para qualquer operação que exige
        recálculo nutricional.

        Pode ser chamado por:
        - Edição manual de participação (após atualizar ms_porcent no DB)
        - Adição/remoção de ingrediente (após modificar IngredienteFormulacao)
        - Alteração de exigência configurada
        - Endpoint explícito POST /formulacoes/{id}/recalcular/
        - MotorAdequacao após geração inicial ou redistribuição

        Em todos os casos, o chamador já deve ter persistido as
        participações atualizadas antes de invocar este service.
        """
        
        # Passo 1-2: Carregar dados do banco
        
        participacao   = IngredienteFormulacaoRepository.get_participacao(formulacao_id)
        vetores        = IngredienteFormulacaoRepository.get_vetores_nutricionais(formulacao_id)
        limites_ingredientes = IngredienteFormulacaoRepository.get_limites_participacao(formulacao_id)
        requisitos     = ExigenciaRepository.get_requisitos(formulacao_id)
        cms_kg         = ExigenciaRepository.get_cms_kg(formulacao_id)
        exigencia_payload = ExigenciaRepository.serializar_configuracao(formulacao_id)
        percentual_alvo_volumoso = Formulacao.objects.values_list(
            "percentual_alvo_volumoso", flat=True
        ).get(pk=formulacao_id)

        if not requisitos:
            raise ValueError(
                f"Formulação {formulacao_id} não possui ExigenciaConfigurada. "
                "Crie a exigência antes de recalcular."
            )
        if cms_kg is None or cms_kg <= 0:
            raise ValueError(
                f"CMS inválido para formulação {formulacao_id}: {cms_kg}. "
                "Verifique a ExigenciaConfigurada."
            )
        if len(participacao) == 0:
            raise ValueError(
                f"Formulação {formulacao_id} não possui ingredientes."
            )

        
        # Passo 3-4: Executar MotorRecalculo (puro, fora da transação)
        
        matriz_M = MotorRecalculo.montar_matriz(vetores)
        entrada  = EntradaRecalculo(
            participacao=participacao,
            matriz_M=matriz_M,
            requisitos=requisitos,
            cms_kg=cms_kg,
        )
        saida = MotorRecalculo.calcular(entrada)

        
        # Passo 4b: Executar MotorCusto (puro, fora da transação, best-effort)
        

        saida_custo: SaidaCusto | None = None
        try:
            custos_kg_mn, ms_percentuais = IngredienteFormulacaoRepository.get_dados_custo(
                formulacao_id
            )
            num_animais = IngredienteFormulacaoRepository.get_num_animais(formulacao_id)
            entrada_custo = EntradaCusto(
                fracoes_ms=participacao.fracoes,
                custos_kg_mn=custos_kg_mn,
                ms_percentuais=ms_percentuais,
                cms_total_kg=cms_kg,
                num_animais=num_animais,
            )
            saida_custo = MotorCusto.calcular(entrada_custo)
        except (ValueError, ZeroDivisionError):
            # Best-effort: ausência de dados de custo não pode impedir
            # o recálculo nutricional. saida_custo permanece None e os
            # passos 5b/6/7 tratam isso como "sem indicadores de custo
            # nesta rodada" em vez de propagar a exceção.
            saida_custo = None

        
        # Passos 5-10: Persistência (atômica)
        
        with transaction.atomic():
            # Passo 5: salvar campos calculados em IngredienteFormulacao
            IngredienteFormulacaoRepository.salvar_saida_recalculo(
                formulacao_id=formulacao_id,
                participacao=participacao,
                saida=saida,
            )

            # Passo 5b: salvar indicadores de custo, se o MotorCusto rodou
            if saida_custo is not None:
                IngredienteFormulacaoRepository.salvar_saida_custo(
                    formulacao_id=formulacao_id,
                    ids_ingredientes=participacao.ids_ingredientes,
                    saida=saida_custo,
                )

            # Passo 6: avaliar alertas (nutricionais + limite + custo)
            alertas_nutrientes = MotorAlertas.avaliar(saida.resultado)
            alertas_limites = MotorAlertas.avaliar_limites_ingredientes(
                _montar_itens_limite(participacao, limites_ingredientes)
            )
            alertas_custo = (
                MotorAlertas.avaliar_custo(saida_custo) if saida_custo is not None else []
            )
            alertas_dicts = alertas_nutrientes + alertas_limites + alertas_custo

            # Passo 7: construir payload do snapshot
            versao_anterior = SnapshotRepository.get_versao_atual(formulacao_id)
            payload = _construir_payload(
                formulacao_id=formulacao_id,
                participacao_dicts=participacao.to_dicts(),
                resultado=saida.resultado.to_dict(),
                vetor_total=saida.vetor_total.to_dict(),
                cms_kg=cms_kg,
                percentual_alvo_volumoso=percentual_alvo_volumoso,
                exigencia_configurada=exigencia_payload,
                alertas=alertas_dicts,
                custos=_saida_custo_to_dict(saida_custo),
                usuario_id=usuario_id,
                motivo=motivo,
            )

            # Passo 8: persistir snapshot
            snapshot = SnapshotRepository.criar(
                formulacao_id=formulacao_id,
                payload=payload,
                motivo=motivo,
                usuario_id=usuario_id,
            )

            # Passo 9: upsert alertas
            AlertaRepository.upsert(
                formulacao_id=formulacao_id,
                novos=alertas_dicts,
                versao_num=snapshot.versao_num,
            )

            # Passo 10: registrar evento
            EventoRepository.registrar(
                formulacao_id=formulacao_id,
                tipo_evento=TipoEvento.RECALCULO_SOLICITADO,
                payload={
                    "motivo":           motivo,
                    "versao_anterior":  versao_anterior,
                    "versao_nova":      snapshot.versao_num,
                    "soma_valida":      saida.resultado.soma_valida,
                    "atende_tudo":      saida.resultado.atende_tudo,
                    "n_alertas":        len(alertas_dicts),
                },
                usuario_id=usuario_id,
            )

        return saida


# Helpers

def _montar_itens_limite(
    participacao,
    limites_ingredientes: list[dict],
) -> list[ParticipacaoIngredienteLimite]:
    """
    Combina o ParticipacaoVetor (fracoes atuais) com os metadados de
    limite_max_participacao carregados do banco, casando por
    ing_form_id (não por posição — mais defensivo caso as duas
    listagens algum dia divirjam em ordenação).
    """
    limites_por_id = {item["ing_form_id"]: item for item in limites_ingredientes}

    itens = []
    for pos, ing_form_id in enumerate(participacao.ids_ingredientes):
        meta = limites_por_id.get(ing_form_id, {})
        itens.append(
            ParticipacaoIngredienteLimite(
                ingrediente_formulacao_id=ing_form_id,
                ingrediente_nome=meta.get("nome", "(removido)"),
                fracao_atual=float(participacao.fracoes[pos]),
                limite_max=meta.get("limite_max_fracao"),
            )
        )
    return itens


def _saida_custo_to_dict(saida_custo: SaidaCusto | None) -> dict | None:
    """
    Serializa SaidaCusto para o payload do snapshot. Retorna None
    quando o MotorCusto não pôde rodar nesta rodada (passo 4b) — o
    front trata a ausência do bloco "custos" como "indicadores ainda
    não calculados", não como erro.
    """
    if saida_custo is None:
        return None
    return {
        "custo_ms_kg":               round(saida_custo.custo_ms_kg, 4),
        "custo_mn_kg":               round(saida_custo.custo_mn_kg, 4),
        "custo_animal_dia":          round(saida_custo.custo_animal_dia, 4),
        "custo_lote_dia":            round(saida_custo.custo_lote_dia, 4),
        "tem_ingrediente_sem_preco": saida_custo.tem_ingrediente_sem_preco,
    }


def _construir_payload(
    formulacao_id: int,
    participacao_dicts: list[dict],
    resultado: dict,
    vetor_total: dict,
    cms_kg: float,
    percentual_alvo_volumoso: float,
    exigencia_configurada: dict | None,
    alertas: list[dict],
    custos: dict | None,
    usuario_id: int | None,
    motivo: str,
) -> dict:
    """
    Monta o payload jsonb auto-contido do SnapshotFormulacao.

    schema_version deve ser incrementado se a estrutura do payload
    mudar — permite que o front-end e os endpoints de histórico
    saibam como deserializar cada versão (seção 16 / risco 5).

    schema_version passou de 2 para 3: snapshots antigos não contêm a
    chave "percentual_alvo_volumoso". Neles, a restauração preserva o
    alvo atual da formulação em vez de inventar um valor histórico.
    """
    return {
        "schema_version":   3,
        "formulacao_id":    formulacao_id,
        "motivo":           motivo,
        "usuario_id":       usuario_id,
        "cms_kg":           cms_kg,
        "percentual_alvo_volumoso": percentual_alvo_volumoso,
        "exigencia_configurada": exigencia_configurada,
        "participacoes":    participacao_dicts,
        "vetor_total":      vetor_total,
        "resultado_adequacao": resultado,
        "alertas":          alertas,
        "custos":           custos,
        "nutrientes_ordem": [n.value for n in NUTRIENTES_ORDEM],
    }
