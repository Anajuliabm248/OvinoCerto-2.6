from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from accounts.models import Usuario
from propriedade.models import Propriedade
from .models import Lote
from .serializers import LoteSerializer


class LoteViewSet(viewsets.ModelViewSet):
    serializer_class = LoteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            return Lote.objects.all()
        
        try:
            perfil_usuario = user.perfil_usuario
            # Filtra lotes apenas de propriedades do usuário
            return Lote.objects.filter(propriedade__usuario=perfil_usuario)
        except Usuario.DoesNotExist:
            return Lote.objects.none()
    
    def filter_queryset(self, queryset):
        search = self.request.query_params.get('search', '')
        propriedade_id = self.request.query_params.get('propriedade_id', '')
        
        if search:
            queryset = queryset.filter(
                Q(nome_lote__icontains=search) |
                Q(raca__icontains=search) |
                Q(sistema__icontains=search) |
                Q(categoria__icontains=search) |
                Q(fase__icontains=search)
            )
        
        if propriedade_id:
            queryset = queryset.filter(propriedade_id=propriedade_id)
        
        return queryset
    
    def perform_create(self, serializer):
        """Garante que o lote pertence a uma propriedade do usuário"""
        propriedade_id = self.request.data.get('propriedade')
        
        try:
            propriedade = Propriedade.objects.get(id=propriedade_id)
            perfil_usuario = self.request.user.perfil_usuario
            
            if propriedade.usuario != perfil_usuario and not self.request.user.is_staff:
                return Response(
                    {'detail': 'Você não tem permissão para adicionar lotes a esta propriedade'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer.save()
        except Propriedade.DoesNotExist:
            return Response(
                {'detail': 'Propriedade não encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
