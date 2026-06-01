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
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Propriedade.objects.all()
        
        try:
            perfil_usuario = user.perfil_usuario
            return Propriedade.objects.filter(usuario=perfil_usuario)
        except Usuario.DoesNotExist:
            return Propriedade.objects.none()
    
    def filter_queryset(self, queryset):
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search) |
                Q(cnpj__icontains=search) |
                Q(proprietario__icontains=search) |
                Q(telefone__icontains=search) |
                Q(uf__icontains=search) |
                Q(cidade__icontains=search) |
                Q(localidade__icontains=search)
            )
        return queryset
    
    def perform_create(self, serializer):
        """Associa a propriedade ao usuário autenticado"""
        try:
            perfil_usuario = self.request.user.perfil_usuario
            serializer.save(usuario=perfil_usuario)
        except Usuario.DoesNotExist:
            return Response(
                {'detail': 'Complete seu perfil antes de criar uma propriedade'},
                status=status.HTTP_400_BAD_REQUEST
            )
