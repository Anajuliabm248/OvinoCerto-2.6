"""CRUD de propriedades com isolamento entre os usuários do sistema."""

from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from accounts.models import Usuario
from .models import Propriedade
from .serializers import PropriedadeSerializer

# pylint: disable= no-member, too-many-ancestors

class PropriedadeViewSet(viewsets.ModelViewSet):
    """
    Administra somente propriedades visíveis para a conta autenticada.

    A associação com o perfil é feita pelo servidor e nunca aceita um usuário
    arbitrário enviado no corpo da requisição.
    - GET  /api/propriedades/            → lista todas as propriedades do usuário logado
    - GET  /api/propriedades/?search=    → busca por nome, proprietário, 
                                            uf, cidade ou localidade
    - POST /api/propriedades/            → cria uma nova propriedade 
                                            (associada ao usuário logado)
    - PUT/PATCH /api/propriedades/{id}/  → atualiza uma propriedade (só as próprias)
    - DELETE /api/propriedades/{id}/     → exclui uma propriedade (só as próprias)
    """
    serializer_class = PropriedadeSerializer
    permission_classes = [IsAuthenticated]

    # Queryset restrito ao usuário autenticado
    def get_queryset(self):
        """Restringe usuários comuns às próprias propriedades."""
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Propriedade.objects.select_related('usuario').all()
        try:
            perfil = user.perfil_usuario
            return Propriedade.objects.filter(usuario=perfil).select_related('usuario')
        except Usuario.DoesNotExist:
            return Propriedade.objects.none()

    def filter_queryset(self, queryset):
        """Busca o texto informado nos principais dados de identificação e local."""
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search)
                | Q(proprietario__icontains=search)
                | Q(uf__icontains=search)
                | Q(cidade__icontains=search)
                | Q(localidade__icontains=search)
            )
        return queryset

    # Associa automaticamente ao perfil do usuário logado
    def perform_create(self, serializer):
        """Associa a propriedade ao perfil autenticado ou explica a falta dele."""
        try:
            perfil = self.request.user.perfil_usuario
            serializer.save(usuario=perfil)
        except Usuario.DoesNotExist as exc:
            raise serializers.ValidationError(
                {'detail': 'Complete seu perfil antes de criar uma propriedade.'}
            ) from exc
