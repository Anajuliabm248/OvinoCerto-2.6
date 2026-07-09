"""viewset do app de propriedade"""

from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from accounts.models import Usuario
from .models import Propriedade
from .serializers import PropriedadeSerializer

# pylint: disable= no-member, too-many-ancestors

class PropriedadeViewSet(viewsets.ModelViewSet):
    '''
    ViewSet para o modelo Propriedade
    - GET  /api/propriedades/            → lista todas as propriedades do usuário logado
    - GET  /api/propriedades/?search=    → busca por nome, cnpj, proprietário, 
                                            uf, cidade ou localidade
    - POST /api/propriedades/            → cria uma nova propriedade 
                                            (associada ao usuário logado)
    - PUT/PATCH /api/propriedades/{id}/  → atualiza uma propriedade (só as próprias)
    - DELETE /api/propriedades/{id}/     → exclui uma propriedade (só as próprias)
    '''
    serializer_class = PropriedadeSerializer
    permission_classes = [IsAuthenticated]

    # Queryset restrito ao usuário autenticado
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

    # Associa automaticamente ao perfil do usuário logado
    def perform_create(self, serializer):
        try:
            perfil = self.request.user.perfil_usuario
            serializer.save(usuario=perfil)
        except Usuario.DoesNotExist as exc:
            raise serializers.ValidationError(
                {'detail': 'Complete seu perfil antes de criar uma propriedade.'}
            ) from exc
