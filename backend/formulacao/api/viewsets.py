"""
ViewSet DRF para o módulo de formulação.

Responsabilidade única: tradução HTTP <-> Application Services.

Para o DRF browsable API renderizar formulários HTML nativos (não JSON),
dois ajustes foram feitos:

1. get_serializer_class() mapeia CADA action ao serializer de entrada
   correto. O browsable API chama get_serializer() ao montar o formulário
   da página — sem esse mapa ele não sabe o que renderizar.

2. Todas as actions usam self.get_serializer(data=request.data) em vez
   de instanciar o serializer diretamente. get_serializer() injeta o
   context automaticamente (request, format, view), necessário para os
   querysets dinâmicos de lote e ingrediente.

Os campos dos serializers de entrada têm style={"base_template": ...}
que instrui o renderer HTML a usar <select>, <select multiple>,
<input> ou <textarea> em vez do textarea JSON padrão.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from formulacao.api.listagem_exigencias_nrc import listar_sugeridas, listar_todas
from formulacao.api.listagem_ingredientes import listar_ingredientes_disponiveis
from formulacao.api.serializers import (
    AdicionarIngredienteInputSerializer,
    AjustarParticipacaoInputSerializer,
    AlertaSerializer,
    AtualizarExigenciaInputSerializer,
    ConfiguracaoNutrienteSerializer,
    EventoFormulacaoSerializer,
    ExigenciaNRCSerializer,
    FormulacaoDetailSerializer,
    FormulacaoListSerializer,
    GerarFormulacaoInicialInputSerializer,
    IngredienteDisponivelSerializer,
    IngredienteFormulacaoSerializer,
    IniciarFormulacaoInputSerializer,
    ResultadoAdequacaoOutputSerializer,
    SnapshotDetailSerializer,
    SnapshotListSerializer,
    SugestaoIngredienteSerializer,
)
from formulacao.models import Formulacao
from formulacao.repositories import AlertaRepository, EventoRepository, SnapshotRepository
from formulacao.services import (
    AdicionarIngredienteService,
    AjustarParticipacaoService,
    AtualizarExigenciaService,
    GerarFormulacaoInicialService,
    IniciarFormulacaoService,
    RecalcularFormulacaoService,
    RemoverIngredienteService,
    RestaurarVersaoService,
    SugerirIngredientesService,
)
from lote.models import Lote


class _NRCPagination(PageNumberPagination):
    page_size             = 20
    page_size_query_param = "page_size"
    max_page_size         = 100


# Mapa de action → serializer de entrada (usado em get_serializer_class e
# consequentemente pelo browsable API para renderizar o formulário HTML).
_INPUT_SERIALIZER_MAP = {
    "create":                IniciarFormulacaoInputSerializer,
    "iniciar":               IniciarFormulacaoInputSerializer,
    "gerar":                 GerarFormulacaoInicialInputSerializer,
    "atualizar_exigencia":   AtualizarExigenciaInputSerializer,
    "adicionar_ingrediente": AdicionarIngredienteInputSerializer,
    "ajustar_ingrediente":   AjustarParticipacaoInputSerializer,
}


class FormulacaoViewSet(viewsets.ModelViewSet):
    """
    ViewSet central de formulação.

    Rotas principais
    ----------------
    GET    /formulacoes/                              lista das formulações do usuário
    POST   /formulacoes/                              atalho para /iniciar/
    GET    /formulacoes/{id}/                         detalhe completo

    Pré-formulação
    --------------
    GET    /formulacoes/exigencias-nrc/?lote_id=X     sugestões de NRC para o lote
    GET    /formulacoes/exigencias-nrc/?todas=true    catálogo completo paginado
    GET    /formulacoes/ingredientes-disponiveis/     catálogo ordenado volumoso→concentrado

    Fluxo de criação
    ----------------
    POST   /formulacoes/iniciar/                      etapa 1: lote + NRC + título
    POST   /formulacoes/{id}/gerar/                   etapa 2: ingredientes → distribuição inicial

    Exigência configurada
    ---------------------
    GET    /formulacoes/{id}/exigencia/
    PATCH  /formulacoes/{id}/exigencia/{NUTRIENTE}/

    Ingredientes na formulação
    --------------------------
    POST   /formulacoes/{id}/ingredientes/
    DELETE /formulacoes/{id}/ingredientes/{ing_form_id}/
    PATCH  /formulacoes/{id}/ingredientes/{ing_form_id}/ajustar/
    POST   /formulacoes/{id}/ingredientes/{ing_form_id}/destravar/

    Recálculo e resultado
    ---------------------
    POST   /formulacoes/{id}/recalcular/
    GET    /formulacoes/{id}/resultado/

    Sugestões
    ---------
    GET    /formulacoes/{id}/sugestoes/
           ?modo=adicionar|substituir  &ing_form_id=X  &max_resultados=10

    Versões (snapshots)
    -------------------
    GET    /formulacoes/{id}/versoes/
    GET    /formulacoes/{id}/versoes/{num}/
    POST   /formulacoes/{id}/versoes/{num}/restaurar/

    Auditoria
    ---------
    GET    /formulacoes/{id}/eventos/
    """

    permission_classes = [IsAuthenticated]
    serializer_class   = FormulacaoDetailSerializer

    # ------------------------------------------------------------------
    # Queryset e serializer
    # ------------------------------------------------------------------

    def get_queryset(self):
        return self._qs_do_usuario(self.request)

    def get_serializer_class(self):
        """
        Retorna o serializer correto por action.
        O browsable API usa este método para montar o formulário HTML
        da página — sem o mapa, todas as actions POST/PATCH mostrariam
        apenas o textarea JSON genérico.
        """
        return _INPUT_SERIALIZER_MAP.get(self.action, FormulacaoDetailSerializer)

    def get_serializer(self, *args, **kwargs):
        """
        Para actions de entrada (POST/PATCH com input serializers customizados),
        não passa a instância ao serializer para evitar que o DRF tente extrair
        campos do modelo que não existem (ex: ms_porcent em AjustarParticipacaoInputSerializer).
        """
        if self.action in _INPUT_SERIALIZER_MAP:
            kwargs.pop('instance', None)
        return super().get_serializer(*args, **kwargs)

    # ------------------------------------------------------------------
    # Listagem / detalhe
    # ------------------------------------------------------------------

    def list(self, request):
        qs = self._qs_do_usuario(request).order_by("-dt_inc")
        return Response(FormulacaoListSerializer(qs, many=True).data)

    def retrieve(self, request, pk=None):
        obj = self._get_formulacao(request, pk)
        return Response(FormulacaoDetailSerializer(obj).data)

    def create(self, request):
        """POST /formulacoes/  →  atalho para /iniciar/."""
        return self._iniciar_formulacao(request)

    # ------------------------------------------------------------------
    # Exigências NRC disponíveis
    # ------------------------------------------------------------------

    @action(detail=False, methods=["get"], url_path="exigencias-nrc")
    def exigencias_nrc(self, request):
        """
        GET /formulacoes/exigencias-nrc/?lote_id=X
        GET /formulacoes/exigencias-nrc/?todas=true&page=N
        """
        lote_id = request.query_params.get("lote_id")
        todas   = request.query_params.get("todas", "").lower() in ("1", "true", "sim")

        if todas:
            qs        = listar_todas()
            paginator = _NRCPagination()
            page      = paginator.paginate_queryset(qs, request)
            return paginator.get_paginated_response(
                ExigenciaNRCSerializer(page, many=True).data
            )

        if not lote_id:
            return Response(
                {"detail": "Informe 'lote_id' para sugestões, ou 'todas=true' para o catálogo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lote = self._get_lote(request, lote_id)
        return Response(ExigenciaNRCSerializer(listar_sugeridas(lote), many=True).data)

    # ------------------------------------------------------------------
    # Catálogo de ingredientes
    # ------------------------------------------------------------------

    @action(detail=False, methods=["get"], url_path="ingredientes-disponiveis")
    def ingredientes_disponiveis(self, request):
        """GET /formulacoes/ingredientes-disponiveis/"""
        perfil = self._perfil(request)
        qs     = listar_ingredientes_disponiveis(usuario_id=perfil.id if perfil else None)
        return Response(IngredienteDisponivelSerializer(qs, many=True).data)

    # ------------------------------------------------------------------
    # Etapa 1: iniciar formulação
    # ------------------------------------------------------------------

    @action(detail=False, methods=["post"], url_path="iniciar")
    def iniciar(self, request):
        """POST /formulacoes/iniciar/"""
        return self._iniciar_formulacao(request)

    def _iniciar_formulacao(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            perfil     = self._perfil(request)
            formulacao = IniciarFormulacaoService.executar(
                lote_id          =ser.validated_data["lote_id"].pk,
                exigencia_nrc_id =ser.validated_data["exigencia_nrc_id"].pk,
                usuario_id       =perfil.id if perfil else None,
                titulo           =ser.validated_data["titulo"],
                observacoes      =ser.validated_data.get("observacoes", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            FormulacaoDetailSerializer(formulacao).data,
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # Etapa 2: gerar distribuição inicial
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="gerar")
    def gerar(self, request, pk=None):
        """
        POST /formulacoes/{id}/gerar/

        Selecione os ingredientes no campo multi-seleção e ajuste o
        percentual-alvo de volumosos se necessário.
        """
        self._get_formulacao(request, pk)

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            perfil     = self._perfil(request)
            formulacao = GerarFormulacaoInicialService.executar(
                formulacao_id            =int(pk),
                ingrediente_ids          =[i.pk for i in ser.validated_data["ingrediente_ids"]],
                usuario_id               =perfil.id if perfil else None,
                percentual_alvo_volumoso =ser.validated_data["percentual_alvo_volumoso"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(FormulacaoDetailSerializer(formulacao).data)

    # ------------------------------------------------------------------
    # Exigência configurada
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get"], url_path="exigencia")
    def exigencia(self, request, pk=None):
        """GET /formulacoes/{id}/exigencia/"""
        formulacao = self._get_formulacao(request, pk)
        try:
            configs = (
                formulacao.exigencia_configurada
                .configuracoes_nutrientes.all()
                .order_by("nutriente")
            )
        except Exception:
            return Response([])
        return Response(ConfiguracaoNutrienteSerializer(configs, many=True).data)

    @action(detail=True, methods=["patch"], url_path=r"exigencia/(?P<nutriente>[A-Z_]+)")
    def atualizar_exigencia(self, request, pk=None, nutriente=None):
        """
        PATCH /formulacoes/{id}/exigencia/{NUTRIENTE}/

        Exemplos de corpo:
          {"operador": ">=",    "valor": 14.0}
          {"operador": "<=",    "valor": 35.0}
          {"operador": "ENTRE", "valor_min": 14.0, "valor_max": 18.0}
          {"operador": "=",     "valor": 15.0}
        """
        self._get_formulacao(request, pk)

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        try:
            perfil = self._perfil(request)
            config = AtualizarExigenciaService.executar(
                formulacao_id=int(pk),
                nutriente    =nutriente,
                operador     =d["operador"],
                valor        =d.get("valor"),
                valor_min    =d.get("valor_min"),
                valor_max    =d.get("valor_max"),
                usuario_id   =perfil.id if perfil else None,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ConfiguracaoNutrienteSerializer(config).data)

    # ------------------------------------------------------------------
    # Ingredientes: adicionar / remover / ajustar / destravar
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="ingredientes")
    def adicionar_ingrediente(self, request, pk=None):
        """POST /formulacoes/{id}/ingredientes/"""
        self._get_formulacao(request, pk)

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            perfil   = self._perfil(request)
            ing_form = AdicionarIngredienteService.executar(
                formulacao_id =int(pk),
                ingrediente_id=ser.validated_data["ingrediente_id"].pk,
                usuario_id    =perfil.id if perfil else None,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            IngredienteFormulacaoSerializer(ing_form).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"ingredientes/(?P<ing_form_id>\d+)",
    )
    def remover_ingrediente(self, request, pk=None, ing_form_id=None):
        """DELETE /formulacoes/{id}/ingredientes/{ing_form_id}/"""
        self._get_formulacao(request, pk)

        try:
            perfil = self._perfil(request)
            RemoverIngredienteService.executar(
                formulacao_id=int(pk),
                ing_form_id  =int(ing_form_id),
                usuario_id   =perfil.id if perfil else None,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"ingredientes/(?P<ing_form_id>\d+)/ajustar",
    )
    def ajustar_ingrediente(self, request, pk=None, ing_form_id=None):
        """
        PATCH /formulacoes/{id}/ingredientes/{ing_form_id}/ajustar/

        Corpo: {"ms_porcent": 35.5}

        Trava o ingrediente (MANUAL_TRAVADA) e dispara o recálculo.
        Retorna a formulação completa atualizada.
        """
        self._get_formulacao(request, pk)

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            perfil = self._perfil(request)
            AjustarParticipacaoService.ajustar(
                formulacao_id=int(pk),
                ing_form_id  =int(ing_form_id),
                nova_fracao  =ser.get_fracao(),
                usuario_id   =perfil.id if perfil else None,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        formulacao = Formulacao.objects.get(pk=pk)
        return Response(FormulacaoDetailSerializer(formulacao).data)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"ingredientes/(?P<ing_form_id>\d+)/destravar",
    )
    def destravar_ingrediente(self, request, pk=None, ing_form_id=None):
        """
        POST /formulacoes/{id}/ingredientes/{ing_form_id}/destravar/

        Remove a trava MANUAL_TRAVADA, liberando o ingrediente para
        redistribuição automática na próxima operação.
        """
        self._get_formulacao(request, pk)

        try:
            perfil = self._perfil(request)
            AjustarParticipacaoService.destravar(
                formulacao_id=int(pk),
                ing_form_id  =int(ing_form_id),
                usuario_id   =perfil.id if perfil else None,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        formulacao = Formulacao.objects.get(pk=pk)
        return Response(FormulacaoDetailSerializer(formulacao).data)

    # ------------------------------------------------------------------
    # Recálculo explícito
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="recalcular")
    def recalcular(self, request, pk=None):
        """
        POST /formulacoes/{id}/recalcular/

        Idempotente — recalcula sem alterar participações.
        Útil após mudar exigências configuradas sem redistribuir.
        """
        self._get_formulacao(request, pk)

        try:
            perfil = self._perfil(request)
            RecalcularFormulacaoService.executar(
                formulacao_id=int(pk),
                usuario_id   =perfil.id if perfil else None,
                motivo       ="recálculo explícito",
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        formulacao = Formulacao.objects.get(pk=pk)
        return Response(FormulacaoDetailSerializer(formulacao).data)

    # ------------------------------------------------------------------
    # Resultado de adequação + alertas
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get"], url_path="resultado")
    def resultado(self, request, pk=None):
        """GET /formulacoes/{id}/resultado/"""
        self._get_formulacao(request, pk)

        snapshot = SnapshotRepository.get_ultimo(int(pk))
        if snapshot is None:
            return Response(
                {"detail": "Formulação ainda não possui resultado calculado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        resultado_payload = snapshot.payload.get("resultado_adequacao", {})
        alertas_ativos    = AlertaRepository.listar_ativos(int(pk))

        return Response({
            "versao_num":  snapshot.versao_num,
            "cms_kg":      snapshot.payload.get("cms_kg"),
            "resultado":   ResultadoAdequacaoOutputSerializer(resultado_payload).data,
            "vetor_total": snapshot.payload.get("vetor_total", {}),
            "alertas":     AlertaSerializer(alertas_ativos, many=True).data,
        })

    # ------------------------------------------------------------------
    # Sugestões de ingredientes
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get"], url_path="sugestoes")
    def sugestoes(self, request, pk=None):
        """
        GET /formulacoes/{id}/sugestoes/
            ?modo=adicionar           (padrão)
            ?modo=substituir&ing_form_id=X
            ?max_resultados=10        (padrão)
        """
        self._get_formulacao(request, pk)

        modo = request.query_params.get("modo", "adicionar")
        if modo not in ("adicionar", "substituir"):
            return Response(
                {"detail": "Parâmetro 'modo' deve ser 'adicionar' ou 'substituir'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ing_form_id_raw = request.query_params.get("ing_form_id")
        ing_form_id     = int(ing_form_id_raw) if ing_form_id_raw else None

        try:
            max_res = int(request.query_params.get("max_resultados", 10))
        except (TypeError, ValueError):
            max_res = 10

        try:
            perfil    = self._perfil(request)
            resultado = SugerirIngredientesService.executar(
                formulacao_id =int(pk),
                usuario_id    =perfil.id if perfil else None,
                modo          =modo,
                ing_form_id   =ing_form_id,
                max_resultados=max_res,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(SugestaoIngredienteSerializer(resultado, many=True).data)

    # ------------------------------------------------------------------
    # Versões (snapshots)
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get"], url_path="versoes")
    def versoes(self, request, pk=None):
        """GET /formulacoes/{id}/versoes/"""
        self._get_formulacao(request, pk)
        qs = SnapshotRepository.listar(int(pk))
        return Response(SnapshotListSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"], url_path=r"versoes/(?P<versao_num>\d+)")
    def versao_detalhe(self, request, pk=None, versao_num=None):
        """GET /formulacoes/{id}/versoes/{num}/"""
        self._get_formulacao(request, pk)
        try:
            snapshot = SnapshotRepository.get_versao(int(pk), int(versao_num))
        except Exception:
            return Response(
                {"detail": f"Versão {versao_num} não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(SnapshotDetailSerializer(snapshot).data)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"versoes/(?P<versao_num>\d+)/restaurar",
    )
    def restaurar(self, request, pk=None, versao_num=None):
        """
        POST /formulacoes/{id}/versoes/{num}/restaurar/

        Restaura participações do snapshot indicado e gera nova versão.
        O histórico existente não é alterado.
        """
        self._get_formulacao(request, pk)

        try:
            perfil     = self._perfil(request)
            formulacao = RestaurarVersaoService.executar(
                formulacao_id=int(pk),
                versao_num   =int(versao_num),
                usuario_id   =perfil.id if perfil else None,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(FormulacaoDetailSerializer(formulacao).data)

    # ------------------------------------------------------------------
    # Auditoria
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get"], url_path="eventos")
    def eventos(self, request, pk=None):
        """GET /formulacoes/{id}/eventos/"""
        self._get_formulacao(request, pk)
        qs = EventoRepository.listar(int(pk))
        return Response(EventoFormulacaoSerializer(qs, many=True).data)

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @staticmethod
    def _perfil(request):
        return getattr(request.user, "perfil_usuario", None)

    def _qs_do_usuario(self, request):
        if request.user.is_staff or request.user.is_superuser:
            return Formulacao.objects.all()
        perfil = self._perfil(request)
        if perfil is None:
            return Formulacao.objects.none()
        return Formulacao.objects.filter(usuario=perfil)

    def _get_formulacao(self, request, pk):
        return get_object_or_404(self._qs_do_usuario(request), pk=pk)

    def _get_lote(self, request, lote_id):
        qs = Lote.objects.select_related("propriedade__usuario")
        if not (request.user.is_staff or request.user.is_superuser):
            perfil = self._perfil(request)
            qs = qs.filter(propriedade__usuario=perfil) if perfil else Lote.objects.none()
        return get_object_or_404(qs, pk=lote_id)