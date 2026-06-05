from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q

from .models import Usuario
from .serializers import UsuarioSerializer, RegisterSerializer, LoginSerializer


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/  →  cria usuário e devolve tokens JWT."""
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
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
    """POST /api/auth/login/  →  valida credenciais e devolve tokens JWT."""
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
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

class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Usuario.objects.select_related('user').all()
        try:
            return Usuario.objects.filter(user=user)
        except Usuario.DoesNotExist:
            return Usuario.objects.none()

    def filter_queryset(self, queryset):
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
        """GET /api/usuarios/me/  →  perfil do usuário autenticado."""
        try:
            usuario = request.user.perfil_usuario
            return Response(UsuarioSerializer(usuario).data)
        except Usuario.DoesNotExist:
            return Response(
                {'detail': 'Usuário sem perfil configurado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def atualizar_perfil(self, request, pk=None):
        """PATCH /api/usuarios/{id}/atualizar_perfil/"""
        usuario = self.get_object()
        serializer = self.get_serializer(usuario, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)