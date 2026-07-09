"""
Application Service - RecalcularFormulacaoService.

Orquestra o pipeline completo de recálculo nutricional:

  1. Carrega ParticipacaoVetor e VetorNutricional[] via repositórios
  2. Carrega requisitos (dict[Nutriente, RequisitoNutriente]) e cms_kg
  3. Monta EntradaRecalculo
  4. Executa MotorRecalculo.calcular() → SaidaRecalculo
  5. Persiste campos *_kg via IngredienteFormulacaoRepository
  6. Avalia alertas via MotorAlertas
  7. Constrói payload do snapshot
  8. Persiste SnapshotFormulacao via SnapshotRepository
  9. Faz upsert de alertas via AlertaRepository
  10. Registra EventoFormulacao

Todo o passo 5-10 ocorre dentro de transaction.atomic.
O MotorRecalculo (passo 4) é executado FORA da transação —
é puro e sem I/O, não precisa de lock.

Retorna SaidaRecalculo para que a view possa serializar o resultado
sem precisar re-consultar o banco.
"""

from __future__ import annotations

from django.db import transaction

from formulacao.domain.nutrientes import NUTRIENTES_ORDEM
from formulacao.engines.motor_alertas import MotorAlertas
from formulacao.engines.motor_recalculo import EntradaRecalculo, MotorRecalculo, SaidaRecalculo
from formulacao.models import TipoEvento
from formulacao.repositories import (
    AlertaRepository,
    EventoRepository,
    ExigenciaRepository,
    IngredienteFormulacaoRepository,
    SnapshotRepository,
)


class RecalcularFormulacaoService:

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
        requisitos     = ExigenciaRepository.get_requisitos(formulacao_id)
        cms_kg         = ExigenciaRepository.get_cms_kg(formulacao_id)
        exigencia_payload = ExigenciaRepository.serializar_configuracao(formulacao_id)

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

        
        # Passos 5-10: Persistência (atômica)
        
        with transaction.atomic():
            # Passo 5: salvar campos calculados em IngredienteFormulacao
            IngredienteFormulacaoRepository.salvar_saida_recalculo(
                formulacao_id=formulacao_id,
                participacao=participacao,
                saida=saida,
            )

            # Passo 6: avaliar alertas
            alertas_dicts = MotorAlertas.avaliar(saida.resultado)

            # Passo 7: construir payload do snapshot
            versao_anterior = SnapshotRepository.get_versao_atual(formulacao_id)
            payload = _construir_payload(
                formulacao_id=formulacao_id,
                participacao_dicts=participacao.to_dicts(),
                resultado=saida.resultado.to_dict(),
                vetor_total=saida.vetor_total.to_dict(),
                cms_kg=cms_kg,
                exigencia_configurada=exigencia_payload,
                alertas=alertas_dicts,
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

def _construir_payload(
    formulacao_id: int,
    participacao_dicts: list[dict],
    resultado: dict,
    vetor_total: dict,
    cms_kg: float,
    exigencia_configurada: dict | None,
    alertas: list[dict],
    usuario_id: int | None,
    motivo: str,
) -> dict:
    """
    Monta o payload jsonb auto-contido do SnapshotFormulacao.

    schema_version deve ser incrementado se a estrutura do payload
    mudar — permite que o front-end e os endpoints de histórico
    saibam como deserializar cada versão (seção 16 / risco 5).
    """
    return {
        "schema_version":   1,
        "formulacao_id":    formulacao_id,
        "motivo":           motivo,
        "usuario_id":       usuario_id,
        "cms_kg":           cms_kg,
        "exigencia_configurada": exigencia_configurada,
        "participacoes":    participacao_dicts,
        "vetor_total":      vetor_total,
        "resultado_adequacao": resultado,
        "alertas":          alertas,
        "nutrientes_ordem": [n.value for n in NUTRIENTES_ORDEM],
    }
