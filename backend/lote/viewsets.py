"""Endpoints de lotes, sempre isolados pela propriedade do usuário."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied
from django.db.models import Q


from exigencia_nrc.serializers import ExigenciaNRCSerializer
from formulacao.api.listagem_exigencias_nrc import listar_sugeridas
from accounts.models import Usuario
from propriedade.models import Propriedade
from .models import Lote
from .serializers import LoteSerializer

# pylint: disable= no-member, unused-argument, too-many-ancestors

class LoteViewSet(viewsets.ModelViewSet):
    """
    Permite administrar os lotes que pertencem ao usuário autenticado.

    Além do CRUD, fornece as linhas NRC mais próximas para que a pessoa
    escolha conscientemente a referência usada na formulação.
    - GET  /api/lotes/                → todos os lotes do usuário logado
    - GET  /api/lotes/?search=        → busca por nome, raça, sistema, categoria ou fase
    - GET  /api/lotes/?propriedade_id= → filtra por propriedade
    - POST /api/lotes/                → cria lote (propriedade deve pertencer ao usuário)
    - PUT/PATCH /api/lotes/{id}/      → edita lote (propriedade deve pertencer ao usuário)
    - DELETE /api/lotes/{id}/         → exclui lote (propriedade deve pertencer ao usuário)
    - GET  /api/lotes/{id}/exigencia/ → sugere exigências NRC para escolha manual do usuário
    """
    serializer_class = LoteSerializer
    permission_classes = [IsAuthenticated]

    # Queryset restrito ao usuário autenticado (via propriedade)
    def get_queryset(self):
        """Retorna apenas lotes próprios; administradores enxergam todos."""
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
        """Aplica busca textual e filtro opcional por propriedade."""
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

    # Garante que a propriedade pertence ao usuário logado
    def perform_create(self, serializer):
        """Confirma a propriedade antes de vincular e salvar o novo lote."""
        propriedade_id = self.request.data.get('propriedade')
        try:
            propriedade = self._get_propriedade_permitida(propriedade_id)
        except Propriedade.DoesNotExist as exc:
            raise NotFound('Propriedade não encontrada.') from exc

        # Passa a propriedade validada diretamente para o save do serializer
        serializer.save(propriedade=propriedade)

    def _get_propriedade_permitida(self, propriedade_id):
        """Busca uma propriedade dentro do conjunto permitido ao usuário atual."""
        qs = Propriedade.objects.all()
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            try:
                perfil = self.request.user.perfil_usuario
            except Usuario.DoesNotExist as exc:
                raise PermissionDenied(
                    'Complete seu perfil antes de cadastrar lotes.'
                ) from exc
            qs = qs.filter(usuario=perfil)
        return qs.get(pk=propriedade_id)

    # Ação: sugere exigências NRC para escolha manual do usuário
    # GET /api/lotes/{id}/exigencia/
    @action(detail=True, methods=['get'])
    def exigencia(self, request, pk=None):
        """Retorna exigências NRC sugeridas; não escolhe automaticamente."""
        lote = self.get_object()

        qs = listar_sugeridas(lote)

        if not qs.exists():
            return Response(
                {'detail': 'Nenhuma exigência NRC sugerida para este lote.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({
            'detail': 'Escolha uma exigência NRC para usar como ponto de partida.',
            'resultados': ExigenciaNRCSerializer(qs, many=True).data,
        })
