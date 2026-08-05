"""
Application Service - AjustarParticipacaoService.

Gerencia dois casos de uso relacionados à participação manual:

  1. ajustar(): usuário edita a % MS de um ingrediente.
     - Valida a fração.
     - Valida que travar este valor não torna 100% matematicamente
       impossível (ver _validar_travamento_possivel).
     - Registra o valor anterior no EventoFormulacao.
     - Persiste nova fração e marca o ingrediente como MANUAL_TRAVADA.
     - Redistribui os ingredientes CALCULADA restantes via
       MotorAdequacao.redistribuir(), para que a soma feche em 100%
       — mesmo padrão de AdicionarIngredienteService/
       RemoverIngredienteService. Só o ingrediente travado por esta
       chamada e os demais MANUAL_TRAVADA ficam intocados.
     - Dispara RecalcularFormulacaoService (recalcula nutrientes,
       gera alertas, cria snapshot).

  2. destravar(): usuário devolve o controle do ingrediente ao sistema.
     - Marca origem_participacao como CALCULADA.
     - Redistribui os ingredientes CALCULADA (incluindo o recém
       destravado) para fechar 100% — antes o valor travado ficava
       intocado até a PRÓXIMA redistribuição disparada por outra
       ação; agora destravar já dispara a redistribuição.
     - Dispara RecalcularFormulacaoService.

INVARIANTE RÍGIDO (requisito de negócio): a soma de participações de
uma formulação com ingredientes deve fechar em exatamente 100% sempre
que houver pelo menos um ingrediente CALCULADA livre para absorver a
diferença. Isso deixou de ser "gera alerta se não fechar" — agora o
motor SEMPRE redistribui os livres para fechar a soma
(MotorAdequacao._normalizar_soma_exata garante isso por construção,
não por tolerância). O único caso em que a soma pode não fechar em
100% é quando NÃO HÁ ingrediente livre para compensar (todos
MANUAL_TRAVADA) — esse caso agora é REJEITADO no momento do
travamento (ValueError), não mais silenciosamente permitido com um
alerta depois.

Separação de responsabilidades:
  - Validações de domínio (fração fora de [0,1], ingrediente não
    pertence à formulação, travamento inviável) → levantam ValueError
    → view retorna 400.
  - Desvio de metas NUTRICIONAIS (não de soma) → não bloqueia, gera
    alerta via MotorAlertas dentro do RecalcularFormulacaoService.
"""

from __future__ import annotations

from django.db import transaction

from formulacao.domain.participacao import OrigemParticipacao
from formulacao.engines.motor_adequacao import MotorAdequacao
from formulacao.engines.motor_recalculo import MotorRecalculo
from formulacao.models import IngredienteFormulacao, OrigemParticipacaoChoices, TipoEvento
from formulacao.repositories import (
    EventoRepository,
    ExigenciaRepository,
    IngredienteFormulacaoRepository,
)
from formulacao.services._configuracao_ingrediente import configuracao_a_partir_do_ingrediente
from formulacao.services.recalcular_formulacao_service import RecalcularFormulacaoService

# Tolerância só para a VALIDAÇÃO de travamento (float noise ao redor
# de 1.0) — não confundir com a normalização exata do motor, que não
# usa tolerância nenhuma, usa divisão.
_TOLERANCIA_VALIDACAO = 1e-6


class AjustarParticipacaoService:

    @staticmethod
    @transaction.atomic
    def ajustar(
        formulacao_id: int,
        ing_form_id: int,
        nova_fracao: float,
        usuario_id: int | None = None,
    ) -> None:
        """
        Edita manualmente a participação de um ingrediente.

        nova_fracao : valor em 0-1 (o serializer converte de % para fração).
        """
        # ------------------------------------------------------------------
        # Validação
        # ------------------------------------------------------------------
        if not (0.0 <= nova_fracao <= 1.0):
            raise ValueError(
                f"nova_fracao deve estar entre 0 e 1 (recebido {nova_fracao}). "
                "O serializer deve converter o percentual enviado pelo front."
            )

        ing_form = AjustarParticipacaoService._get_e_validar(
            formulacao_id, ing_form_id
        )

        fracao_anterior = ing_form.ms_porcent / 100.0

        # ------------------------------------------------------------------
        # Nenhuma mudança real → encerra sem criar snapshot desnecessário
        # ------------------------------------------------------------------
        if abs(nova_fracao - fracao_anterior) < 1e-9:
            return

        # ------------------------------------------------------------------
        # Valida que este travamento não torna 100% impossível
        # ------------------------------------------------------------------
        participacao_atual = IngredienteFormulacaoRepository.get_participacao(formulacao_id)
        tem_livre_restante = AjustarParticipacaoService._validar_travamento_possivel(
            participacao_atual=participacao_atual,
            ing_form_id=ing_form_id,
            nova_fracao=nova_fracao,
        )

        # ------------------------------------------------------------------
        # Persistir nova participação e travar
        # ------------------------------------------------------------------
        IngredienteFormulacaoRepository.atualizar_participacao(
            ing_form_id=ing_form_id,
            fracao=nova_fracao,
            origem=OrigemParticipacao.MANUAL_TRAVADA,
        )

        # ------------------------------------------------------------------
        # Redistribuir os ingredientes livres restantes para fechar 100%
        # ------------------------------------------------------------------
        resultado_dist = None
        if tem_livre_restante:
            resultado_dist = AjustarParticipacaoService._redistribuir_livres(formulacao_id)

        # ------------------------------------------------------------------
        # Registrar evento antes do recálculo
        # ------------------------------------------------------------------
        nome_ing = ing_form.ingrediente.nome if ing_form.ingrediente else "(removido)"
        EventoRepository.registrar(
            formulacao_id=formulacao_id,
            tipo_evento=TipoEvento.PARTICIPACAO_EDITADA,
            payload={
                "ing_form_id":       ing_form_id,
                "ingrediente_nome":  nome_ing,
                "fracao_anterior":   round(fracao_anterior, 6),
                "fracao_nova":       round(nova_fracao, 6),
                "pct_anterior":      round(fracao_anterior * 100, 4),
                "pct_nova":          round(nova_fracao * 100, 4),
                "redistribuido":     resultado_dist is not None,
                "convergiu":         resultado_dist.convergiu if resultado_dist else None,
            },
            usuario_id=usuario_id,
        )

        # ------------------------------------------------------------------
        # Recalcular nutrientes + snapshot
        # ------------------------------------------------------------------
        nome_ing_curto = nome_ing[:40]
        RecalcularFormulacaoService.executar(
            formulacao_id=formulacao_id,
            usuario_id=usuario_id,
            motivo=f"edição manual: {nome_ing_curto} → {nova_fracao * 100:.1f}%",
        )

    @staticmethod
    @transaction.atomic
    def destravar(
        formulacao_id: int,
        ing_form_id: int,
        usuario_id: int | None = None,
    ) -> None:
        """
        Devolve o controle do ingrediente ao sistema (CALCULADA).

        O ms_porcent atual é mantido — a próxima chamada a
        redistribuir() (via Adicionar/RemoverIngredienteService)
        irá ajustá-lo.
        """
        ing_form = AjustarParticipacaoService._get_e_validar(
            formulacao_id, ing_form_id
        )

        # Já está livre — nada a fazer
        if ing_form.origem_participacao == OrigemParticipacaoChoices.CALCULADA:
            return

        IngredienteFormulacaoRepository.atualizar_participacao(
            ing_form_id=ing_form_id,
            fracao=ing_form.ms_porcent / 100.0,   # mantém valor atual até a redistribuição
            origem=OrigemParticipacao.CALCULADA,
        )

        resultado_dist = AjustarParticipacaoService._redistribuir_livres(formulacao_id)

        nome_ing = ing_form.ingrediente.nome if ing_form.ingrediente else "(removido)"
        EventoRepository.registrar(
            formulacao_id=formulacao_id,
            tipo_evento=TipoEvento.PARTICIPACAO_DESTRAVADA,
            payload={
                "ing_form_id":      ing_form_id,
                "ingrediente_nome": nome_ing,
                "fracao_atual":     round(ing_form.ms_porcent / 100.0, 6),
                "convergiu":        resultado_dist.convergiu,
            },
            usuario_id=usuario_id,
        )

        RecalcularFormulacaoService.executar(
            formulacao_id=formulacao_id,
            usuario_id=usuario_id,
            motivo=f"destravamento: {nome_ing[:40]}",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validar_travamento_possivel(
        participacao_atual,
        ing_form_id: int,
        nova_fracao: float,
    ) -> bool:
        """
        Verifica se travar `ing_form_id` em `nova_fracao` deixa a soma
        de 100% matematicamente alcançável.

        Retorna True se sobra pelo menos 1 ingrediente CALCULADA para
        absorver a diferença (caso normal — redistribuir() cuidará do
        resto). Retorna False só quando TODOS os ingredientes já são
        MANUAL_TRAVADA (incluindo este) — nesse caso a soma dos
        travados TEM que já fechar em 100% sozinha, senão não há como
        completar.

        Levanta ValueError (não deixa a operação prosseguir) quando:
          - Os travados (outros + este) já ultrapassam 100% sozinhos
            — nenhum CALCULADA pode "compensar" isso ficando negativo.
          - Não sobra nenhum CALCULADA E os travados não fecham
            exatamente em 100%.
        """
        soma_outros_travados = 0.0
        n_outros_livres = 0
        for pos, id_atual in enumerate(participacao_atual.ids_ingredientes):
            if id_atual == ing_form_id:
                continue
            if participacao_atual.origens[pos] == OrigemParticipacao.MANUAL_TRAVADA:
                soma_outros_travados += float(participacao_atual.fracoes[pos])
            else:
                n_outros_livres += 1

        soma_travados_apos = soma_outros_travados + nova_fracao

        if soma_travados_apos > 1.0 + _TOLERANCIA_VALIDACAO:
            raise ValueError(
                f"Não é possível travar este ingrediente em "
                f"{nova_fracao * 100:.2f}%: somado aos demais já travados "
                f"({soma_outros_travados * 100:.2f}%), a soma passaria de "
                f"{soma_travados_apos * 100:.2f}%, acima de 100%. "
                "Reduza este valor ou destrave outro ingrediente primeiro."
            )

        if n_outros_livres == 0 and abs(soma_travados_apos - 1.0) > _TOLERANCIA_VALIDACAO:
            raise ValueError(
                f"Não há nenhum ingrediente livre (CALCULADA) para fechar a "
                f"soma em 100%: todos os ingredientes ficariam travados "
                f"somando {soma_travados_apos * 100:.2f}%. Destrave ao menos "
                "um ingrediente para o sistema poder completar os 100% "
                "automaticamente."
            )

        return n_outros_livres > 0

    @staticmethod
    def _redistribuir_livres(formulacao_id: int):
        """
        Recarrega o estado completo da formulação e chama
        MotorAdequacao.redistribuir() sobre os ingredientes CALCULADA,
        aplicando o resultado — mesmo padrão de
        AdicionarIngredienteService/RemoverIngredienteService.

        Retorna o ResultadoDistribuicao (para registrar no evento).
        Levanta ValueError se a formulação não tiver
        ExigenciaConfigurada (não deveria acontecer neste ponto do
        fluxo, mas falha explicitamente em vez de silenciar).
        """
        participacao = IngredienteFormulacaoRepository.get_participacao(formulacao_id)
        vetores       = IngredienteFormulacaoRepository.get_vetores_nutricionais(formulacao_id)
        requisitos    = ExigenciaRepository.get_requisitos(formulacao_id)

        if not requisitos:
            raise ValueError(
                f"Formulação {formulacao_id} não possui ExigenciaConfigurada."
            )

        matriz_M = MotorRecalculo.montar_matriz(vetores)

        ing_form_qs = list(
            IngredienteFormulacao.objects
            .filter(formulacao_id=formulacao_id)
            .select_related("ingrediente")
            .order_by("id")
        )
        configuracoes = [
            configuracao_a_partir_do_ingrediente(obj.ingrediente)
            for obj in ing_form_qs
        ]

        resultado_dist = MotorAdequacao.redistribuir(
            matriz_M=matriz_M,
            requisitos=requisitos,
            participacao_atual=participacao,
            configuracoes=configuracoes,
        )

        ids = participacao.ids_ingredientes
        for pos, ing_form_id in enumerate(ids):
            origem_atual = participacao.origens[pos]
            if origem_atual != OrigemParticipacao.CALCULADA:
                continue  # travados nunca são reescritos por aqui
            IngredienteFormulacaoRepository.atualizar_participacao(
                ing_form_id=ing_form_id,
                fracao=float(resultado_dist.fracoes[pos]),
                origem=OrigemParticipacao.CALCULADA,
            )

        return resultado_dist

    @staticmethod
    def _get_e_validar(
        formulacao_id: int,
        ing_form_id: int,
    ) -> IngredienteFormulacao:
        """
        Retorna o IngredienteFormulacao garantindo que pertence à
        formulação. Levanta ValueError se não encontrado.
        """
        try:
            return (
                IngredienteFormulacao.objects
                .select_related("ingrediente")
                .get(pk=ing_form_id, formulacao_id=formulacao_id)
            )
        except IngredienteFormulacao.DoesNotExist:
            raise ValueError(
                f"IngredienteFormulacao {ing_form_id} não encontrado "
                f"na formulação {formulacao_id}."
            )
