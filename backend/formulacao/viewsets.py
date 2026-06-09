from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from lote.models import Lote
from exigencia_nrc.models import ExigenciaNRC
from exigencia_nrc.serializers import ExigenciaNRCSerializer
from accounts.models import Usuario
from lote.models import FASES_COM_PARTO_E_DIAS

from .models import Formulacao
from .serializers import (
    FormulacaoCreateSerializer,
    FormulacaoDetailSerializer,
    FormulacaoListSerializer,
)
from .services.formulacao_service import FormulacaoService


class FormulacaoViewSet(viewsets.ModelViewSet):
    """
    GET  /api/formulacoes/                          → lista resumida
    POST /api/formulacoes/                          → criar formulação
    GET  /api/formulacoes/{id}/                     → detalhe completo
    GET  /api/formulacoes/lotes_disponiveis/        → lotes do usuário
    GET  /api/formulacoes/exigencia_lote/?lote_id=X → exigência NRC do lote
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Formulacao.objects.select_related(
                'lote', 'usuario', 'exigencia', 'motor_otimizacao'
            ).all()
        try:
            perfil = user.perfil_usuario
            return Formulacao.objects.filter(usuario=perfil).select_related(
                'lote', 'usuario', 'exigencia', 'motor_otimizacao'
            )
        except Usuario.DoesNotExist:
            return Formulacao.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return FormulacaoCreateSerializer
        if self.action == 'retrieve':
            return FormulacaoDetailSerializer
        return FormulacaoListSerializer

    # ── POST /api/formulacoes/ ────────────────────────────────────────
    def create(self, request, *args, **kwargs):
        serializer = FormulacaoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            perfil = request.user.perfil_usuario
        except Usuario.DoesNotExist:
            return Response(
                {'detail': 'Complete seu perfil antes de criar formulações.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            servico = FormulacaoService()
            formulacao, motor, recomendacoes = servico.formular(
                usuario=perfil,
                lote_id=data['lote_id'],
                titulo=data['titulo'],
                objetivo=data['objetivo_otimizacao'],
                observacoes=data.get('observacoes', ''),
                ingredientes_selecionados=data.get('ingredientes_selecionados') or None,
            )
        except (ValueError, PermissionError) as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'detail': f'Erro interno na formulação: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        resp_data = FormulacaoDetailSerializer(formulacao).data

        if motor.status == 'inviavel':
            return Response(resp_data, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response(resp_data, status=status.HTTP_201_CREATED)

    # ── GET /api/formulacoes/{id}/ ────────────────────────────────────
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(FormulacaoDetailSerializer(instance).data)

    # ── GET /api/formulacoes/lotes_disponiveis/ ───────────────────────
    @action(detail=False, methods=['get'])
    def lotes_disponiveis(self, request):
        try:
            perfil = request.user.perfil_usuario
        except Usuario.DoesNotExist:
            return Response([])

        lotes = Lote.objects.filter(
            propriedade__usuario=perfil
        ).select_related('propriedade').values(
            'id', 'nome_lote', 'categoria', 'fase',
            'peso_vivo', 'gmd_esperado', 'num_animais',
        )
        return Response(list(lotes))

    # ── GET /api/formulacoes/exigencia_lote/?lote_id=X ───────────────
    @action(detail=False, methods=['get'])
    def exigencia_lote(self, request):
        lote_id = request.query_params.get('lote_id')
        if not lote_id:
            return Response(
                {'detail': 'Parâmetro lote_id obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lote = Lote.objects.get(pk=lote_id)
        except Lote.DoesNotExist:
            return Response({'detail': 'Lote não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            perfil = request.user.perfil_usuario
            if lote.propriedade.usuario != perfil and not request.user.is_staff:
                return Response({'detail': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)
        except Usuario.DoesNotExist:
            return Response({'detail': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)

        qs = ExigenciaNRC.objects.filter(categoria=lote.categoria, fase=lote.fase)
        if lote.fase in FASES_COM_PARTO_E_DIAS and lote.tipo_parto:
            qs = qs.filter(tipo_parto=lote.tipo_parto)

        if not qs.exists():
            return Response(
                {'detail': 'Nenhuma exigência NRC encontrada para este lote.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        best = min(qs, key=lambda e: abs((e.pv_kg or 0) - lote.peso_vivo))
        mesmo_pv = [e for e in qs if e.pv_kg == best.pv_kg]
        if len(mesmo_pv) > 1 and lote.gmd_esperado:
            best = min(mesmo_pv, key=lambda e: abs((e.gmd_kg or 0) - lote.gmd_esperado))

        return Response(ExigenciaNRCSerializer(best).data)

    # ── Filtros ────────────────────────────────────────────────────────
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        params   = self.request.query_params

        lote_id = params.get('lote_id')
        if lote_id and lote_id.isdigit():
            queryset = queryset.filter(lote_id=int(lote_id))

        objetivo = params.get('objetivo')
        if objetivo and objetivo.upper() in ('CUSTO', 'PB', 'FDN'):
            queryset = queryset.filter(objetivo_otimizacao=objetivo.upper())

        return queryset
