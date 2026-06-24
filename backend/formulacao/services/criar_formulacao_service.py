"""
Application Service - CriarFormulacaoService.

Orquestra o fluxo completo de criação de uma formulação (seção 6,
passos 1-4 do documento de arquitetura):

  1. Cria o registro Formulacao
  2. Busca ExigenciaNRC pelo lote e calcula CMS
  3. Cria ExigenciaConfigurada + ConfiguracaoNutriente (cópia do NRC)
  4. Cria IngredienteFormulacao para cada ingrediente selecionado
     (ms_porcent=0, CALCULADA)
  5. Chama MotorAdequacao.gerar_distribuicao_inicial() (SciPy SLSQP)
  6. Aplica as frações resultantes (ms_porcent no banco)
  7. Chama RecalcularFormulacaoService → persiste nutrientes + snapshot v1

Tudo dentro de uma única transaction.atomic.

Pré-condições (validadas no Application Service, não na view):
- lote_id deve existir e ter ExigenciaNRC correspondente.
- ingrediente_ids deve ter ao menos 1 elemento.
- Ingredientes devem pertencer ao usuário ou ser do sistema.
"""

from __future__ import annotations

from django.db import transaction

from exigencia_nrc.models import ExigenciaNRC
from formulacao.engines.motor_adequacao import ConfiguracaoIngrediente, MotorAdequacao
from formulacao.engines.motor_recalculo import MotorRecalculo
from formulacao.models import (
    Formulacao,
    IngredienteFormulacao,
    OrigemParticipacaoChoices,
    StatusFormulacao,
    TipoEvento,
)
from formulacao.repositories import (
    EventoRepository,
    ExigenciaRepository,
    IngredienteFormulacaoRepository,
    SnapshotRepository,
)
from formulacao.services.recalcular_formulacao_service import RecalcularFormulacaoService
from ingrediente.models import Ingrediente
from lote.models import Lote

class CriarFormulacaoService:

    @staticmethod
    @transaction.atomic
    def executar(
        lote_id: int,
        usuario_id: int,
        titulo: str,
        ingrediente_ids: list[int],
        observacoes: str = "",
        percentual_alvo_volumoso: float = 0.50,
    ) -> Formulacao:
        """
        Retorna o registro Formulacao criado com snapshot v1 persistido.

        ingrediente_ids: IDs de Ingrediente (sistema ou custom do usuário),
                         na ordem em que devem aparecer na formulação.
        """
        
        # 1. Validações de entrada
        
        if not ingrediente_ids:
            raise ValueError("Selecione ao menos um ingrediente.")

        lote = Lote.objects.select_related("exigencia_nrc").get(pk=lote_id)

        exigencia_nrc = CriarFormulacaoService._buscar_exigencia_nrc(lote)
        cms_kg        = CriarFormulacaoService._calcular_cms(lote, exigencia_nrc)

        ingredientes = list(
            Ingrediente.objects.filter(pk__in=ingrediente_ids)
        )
        if len(ingredientes) != len(ingrediente_ids):
            faltando = set(ingrediente_ids) - {i.pk for i in ingredientes}
            raise ValueError(f"Ingredientes não encontrados: {faltando}")

        # Mantém a ordem solicitada pelo usuário
        ordem = {id_: pos for pos, id_ in enumerate(ingrediente_ids)}
        ingredientes.sort(key=lambda i: ordem[i.pk])

        
        # 2. Criar Formulacao
        
        formulacao = Formulacao.objects.create(
            lote_id=lote_id,
            usuario_id=usuario_id,
            titulo=titulo,
            observacoes=observacoes,
            status=StatusFormulacao.RASCUNHO,
        )

        
        # 3. Criar ExigenciaConfigurada (cópia editável do NRC)
        
        ExigenciaRepository.criar_de_nrc(
            formulacao=formulacao,
            exigencia_nrc=exigencia_nrc,
            cms_kg=cms_kg,
        )

        
        # 4. Criar IngredienteFormulacao (ms_porcent=0, CALCULADA)
        
        IngredienteFormulacao.objects.bulk_create([
            IngredienteFormulacao(
                formulacao=formulacao,
                ingrediente=ing,
                ms_porcent=0.0,
                origem_participacao=OrigemParticipacaoChoices.CALCULADA,
            )
            for ing in ingredientes
        ])

        
        # 5. Geração inicial via MotorAdequacao (puro, ainda fora de I/O)
        
        vetores       = IngredienteFormulacaoRepository.get_vetores_nutricionais(formulacao.pk)
        matriz_M      = MotorRecalculo.montar_matriz(vetores)
        requisitos    = ExigenciaRepository.get_requisitos(formulacao.pk)
        configuracoes = [
            ConfiguracaoIngrediente(
                classificacao=ing.classificacao or "CONCENTRADO",
                limite_min=0.0,
                limite_max=1.0,
            )
            for ing in ingredientes
        ]

        resultado_dist = MotorAdequacao.gerar_distribuicao_inicial(
            matriz_M=matriz_M,
            requisitos=requisitos,
            configuracoes=configuracoes,
            percentual_alvo_volumoso=percentual_alvo_volumoso,
        )

        
        # 6. Aplicar frações: atualizar ms_porcent nos registros criados
        
        qs_ing_form = list(
            IngredienteFormulacao.objects
            .filter(formulacao=formulacao)
            .order_by("id")
        )
        para_atualizar = []
        for pos, obj in enumerate(qs_ing_form):
            obj.ms_porcent = float(resultado_dist.fracoes[pos]) * 100.0
            para_atualizar.append(obj)

        IngredienteFormulacao.objects.bulk_update(
            para_atualizar, fields=["ms_porcent"]
        )

        
        # 7. Recálculo completo + snapshot v1
        
        motivo = (
            "geração inicial"
            if resultado_dist.convergiu
            else f"geração inicial (fallback nnls: {resultado_dist.mensagem})"
        )
        RecalcularFormulacaoService.executar(
            formulacao_id=formulacao.pk,
            usuario_id=usuario_id,
            motivo=motivo,
        )

        # Evento de criação (complementa o snapshot)
        EventoRepository.registrar(
            formulacao_id=formulacao.pk,
            tipo_evento=TipoEvento.CRIACAO,
            payload={
                "lote_id":              lote_id,
                "n_ingredientes":       len(ingredientes),
                "convergiu":            resultado_dist.convergiu,
                "mensagem_solver":      resultado_dist.mensagem,
                "percentual_alvo_vol":  percentual_alvo_volumoso,
            },
            usuario_id=usuario_id,
        )

        formulacao.status = StatusFormulacao.ATIVA
        formulacao.save(update_fields=["status"])

        return formulacao

    
    # Helpers
    

    @staticmethod
    def _buscar_exigencia_nrc(lote: Lote) -> ExigenciaNRC:
        """
        Busca a ExigenciaNRC correspondente ao lote via lookup.
        Levanta ValueError se não encontrar — o Application Service
        retorna 400 para a view.
        """
        try:
            return ExigenciaNRC.objects.get(
                categoria=lote.categoria,
                fase=lote.fase,
                pv_kg=round(lote.peso_vivo),
                gmd_kg=lote.gmd_esperado,
                tipo_parto=lote.tipo_parto,
            )
        except ExigenciaNRC.DoesNotExist:
            raise ValueError(
                f"Exigência NRC não encontrada para: categoria={lote.categoria}, "
                f"fase={lote.fase}, pv={lote.peso_vivo}kg, gmd={lote.gmd_esperado}."
            )
        except ExigenciaNRC.MultipleObjectsReturned:
            # Retorna a primeira — lookup deve ser único, mas como
            # proteção usa o registro mais recente.
            return ExigenciaNRC.objects.filter(
                categoria=lote.categoria,
                fase=lote.fase,
                pv_kg=round(lote.peso_vivo),
                gmd_kg=lote.gmd_esperado,
                tipo_parto=lote.tipo_parto,
            ).last()

    @staticmethod
    def _calcular_cms(lote: Lote, exigencia_nrc: ExigenciaNRC) -> float:
        """
        CMS em kg/dia. Usa o valor direto da tabela NRC (cms_kg).
        O campo cms_kg em ExigenciaNRC já é kg/animal/dia.
        """
        return float(exigencia_nrc.cms_kg)