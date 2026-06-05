from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from accounts.models import Usuario
from .models import Propriedade
from .serializers import PropriedadeSerializer


class PropriedadeViewSet(viewsets.ModelViewSet):
    serializer_class = PropriedadeSerializer
    permission_classes = [IsAuthenticated]

    # ------------------------------------------------------------------
    # Queryset restrito ao usuário autenticado
    # ------------------------------------------------------------------
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Propriedade.objects.select_related('usuario').all()
        try:
            perfil = user.perfil_usuario
            return Propriedade.objects.filter(usuario=perfil).select_related('usuario')
        except Usuario.DoesNotExist:
            return Propriedade.objects.none()

    def filter_queryset(self, queryset):
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search)
                | Q(cnpj__icontains=search)
                | Q(proprietario__icontains=search)
                | Q(uf__icontains=search)
                | Q(cidade__icontains=search)
                | Q(localidade__icontains=search)
            )
        return queryset

    # ------------------------------------------------------------------
    # Associa automaticamente ao perfil do usuário logado
    # ------------------------------------------------------------------
    def perform_create(self, serializer):
        try:
            perfil = self.request.user.perfil_usuario
            serializer.save(usuario=perfil)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError(
                {'detail': 'Complete seu perfil antes de criar uma propriedade.'}
            )