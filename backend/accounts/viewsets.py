"""Endpoints de cadastro, login e manutenção do próprio perfil."""
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q

from .models import Usuario
from .serializers import UsuarioSerializer, RegisterSerializer, LoginSerializer

# pylint: disable=abstract-method, no-member, too-many-ancestors, unused-argument


class RegisterView(generics.CreateAPIView):
    """Cria conta e perfil e já entrega os tokens JWT para o primeiro acesso."""
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        """Valida o cadastro, persiste os dois registros e monta a resposta JWT."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()

        refresh = RefreshToken.for_user(usuario.user)
        return Response(
            {
                'access':  str(refresh.access_token),
                'refresh': str(refresh),
                'usuario': UsuarioSerializer(usuario).data,
            },
            status=status.HTTP_201_CREATED,
        )

class LoginView(generics.GenericAPIView):
    """Autentica uma conta ativa e devolve tokens JWT e dados do perfil."""
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Valida as credenciais e serializa o perfil, quando ele existe."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        try:
            usuario_data = UsuarioSerializer(user.perfil_usuario).data
        except Usuario.DoesNotExist:
            usuario_data = None

        return Response(
            {
                'access':  str(refresh.access_token),
                'refresh': str(refresh),
                'usuario': usuario_data,
            }
        )

class UsuarioViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Lista e atualiza perfis visíveis; cadastro continua na rota de registro.

    Usuários comuns enxergam apenas o próprio perfil. Contas administrativas do
    Django podem consultar todos. A API não oferece exclusão de perfil, porque
    apagar somente esta linha deixaria uma conta autenticável órfã.
    """
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Restringe usuários comuns ao próprio perfil e libera a lista ao staff."""
        user = self.request.user
        perfil = getattr(user, 'perfil_usuario', None)
        if user.is_staff or user.is_superuser or (
            perfil and perfil.pode_gerenciar_usuarios
        ):
            return Usuario.objects.select_related('user').all()
        return Usuario.objects.filter(user=user).select_related('user')

    def filter_queryset(self, queryset):
        """Aplica busca textual aos perfis que já passaram pela autorização."""
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search)
                | Q(email__icontains=search)
                | Q(cpf__icontains=search)
                | Q(cidade__icontains=search)
            )
        return queryset

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Retorna o perfil ligado à conta autenticada ou uma resposta 404 clara."""
        perfil = getattr(request.user, 'perfil_usuario', None)
        if perfil is None:
            return Response(
                {'detail': 'Usuário sem perfil configurado.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(UsuarioSerializer(perfil).data)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def atualizar_perfil(self, request, pk=None):
        """Atualiza parcialmente os dados permitidos de um perfil visível."""
        usuario = self.get_object()
        serializer = self.get_serializer(usuario, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
