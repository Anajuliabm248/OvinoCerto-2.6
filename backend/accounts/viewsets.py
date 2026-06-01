from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import Usuario
from .serializers import UsuarioSerializer


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Admin vê todos, usuário comum vê só a si mesmo
        if user.is_staff or user.is_superuser:
            return Usuario.objects.all()
        try:
            return Usuario.objects.filter(user=user)
        except Usuario.DoesNotExist:
            return Usuario.objects.none()
    
    def filter_queryset(self, queryset):
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search) |
                Q(email__icontains=search) |
                Q(cpf__icontains=search) |
                Q(cidade__icontains=search)
            )
        return queryset
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Retorna o perfil do usuário autenticado"""
        try:
            usuario = request.user.perfil_usuario
            serializer = self.get_serializer(usuario)
            return Response(serializer.data)
        except Usuario.DoesNotExist:
            return Response(
                {'detail': 'Usuário sem perfil configurado'},
                status=status.HTTP_404_NOT_FOUND
            )
