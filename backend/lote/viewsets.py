from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.shortcuts import get_object_or_404

from accounts.models import Usuario
from propriedade.models import Propriedade
from .models import Lote
from .serializers import LoteSerializer


class LoteViewSet(viewsets.ModelViewSet):
    serializer_class = LoteSerializer
    permission_classes = [IsAuthenticated]

    # ------------------------------------------------------------------
    # Queryset restrito ao usuário autenticado (via propriedade)
    # ------------------------------------------------------------------
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Lote.objects.select_related('propriedade__usuario').all()
        try:
            perfil = user.perfil_usuario
            return Lote.objects.filter(
                propriedade__usuario=perfil
            ).select_related('propriedade__usuario')
        except Usuario.DoesNotExist:
            return Lote.objects.none()

    def filter_queryset(self, queryset):
        params = self.request.query_params
        search = params.get('search', '')
        propriedade_id = params.get('propriedade_id', '')

        if search:
            queryset = queryset.filter(
                Q(nome_lote__icontains=search)
                | Q(raca__icontains=search)
                | Q(sistema__icontains=search)
                | Q(categoria__icontains=search)
                | Q(fase__icontains=search)
            )
        if propriedade_id:
            queryset = queryset.filter(propriedade_id=propriedade_id)

        return queryset

    # ------------------------------------------------------------------
    # Garante que a propriedade pertence ao usuário logado
    # ------------------------------------------------------------------
    def perform_create(self, serializer):
        propriedade_id = self.request.data.get('propriedade')
        try:
            propriedade = Propriedade.objects.get(pk=propriedade_id)
        except Propriedade.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('Propriedade não encontrada.')

        perfil = self.request.user.perfil_usuario
        if propriedade.usuario != perfil and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                'Você não tem permissão para adicionar lotes a esta propriedade.'
            )
        serializer.save()

    # ------------------------------------------------------------------
    # Ação: busca a exigência NRC correspondente a este lote
    # GET /api/lotes/{id}/exigencia/
    # ------------------------------------------------------------------
    @action(detail=True, methods=['get'])
    def exigencia(self, request, pk=None):
        """Retorna a exigência NRC mais próxima para os parâmetros do lote."""
        lote = self.get_object()

        from exigencia_nrc.models import ExigenciaNRC
        from exigencia_nrc.serializers import ExigenciaNRCSerializer

        qs = ExigenciaNRC.objects.filter(
            categoria=lote.categoria,
            fase=lote.fase,
        )

        # Filtra tipo_parto quando a fase exige
        from lote.models import FASES_COM_PARTO_E_DIAS
        if lote.fase in FASES_COM_PARTO_E_DIAS and lote.tipo_parto:
            qs = qs.filter(tipo_parto=lote.tipo_parto)

        if not qs.exists():
            return Response(
                {'detail': 'Nenhuma exigência NRC encontrada para esta combinação.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Escolhe a linha cujo pv_kg é mais próximo do peso do lote
        best = min(qs, key=lambda e: abs((e.pv_kg or 0) - lote.peso_vivo))

        # Se há múltiplas com mesmo pv_kg, prioriza gmd mais próximo
        mesmo_pv = [e for e in qs if e.pv_kg == best.pv_kg]
        if len(mesmo_pv) > 1 and lote.gmd_esperado:
            best = min(
                mesmo_pv,
                key=lambda e: abs((e.gmd_kg or 0) - lote.gmd_esperado),
            )

        return Response(ExigenciaNRCSerializer(best).data)