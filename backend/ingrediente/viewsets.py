"""API do catálogo compartilhado, ingredientes customizados e preços pessoais."""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q, Case, When, Value, IntegerField
from django.shortcuts import get_object_or_404
from django.db.models.functions import Lower

from accounts.models import Usuario
from .models import (
    CAMPOS_LIMITES_PARTICIPACAO,
    Ingrediente,
    CLASSIFICACAO_CHOICES,
    TIPO_CHOICES,
    PrecoIngredienteUsuario,
    HistoricoPrecoIngrediente,
    OrigemAlteracaoPrecoChoices,
)
from .serializers import AtualizarPrecoCatalogoInputSerializer, IngredienteSerializer


# pylint: disable= no-member, too-many-ancestors, unused-argument

class IngredienteViewSet(viewsets.ModelViewSet):
    """
    Banco de ingredientes.

    - GET  /api/ingredientes/                → todos (Valadares + custom do usuário)
    - GET  /api/ingredientes/?valadares=true → somente Valadares
    - GET  /api/ingredientes/?valadares=false→ somente custom do usuário
    - GET  /api/ingredientes/?classificacao= → filtro
    - GET  /api/ingredientes/?tipo=          → filtro
    - GET  /api/ingredientes/?search=        → busca por nome
    - GET  /api/ingredientes/meus/           → atalho: só custom do usuário
    - POST /api/ingredientes/               → cria ingrediente custom
    - PATCH /api/ingredientes/{id}/preco/        → atualiza preço do ingrediente (qualquer, Valadares incluso)
    - PUT/PATCH /api/ingredientes/{id}/     → edita ingredientes próprios
    - PATCH /api/ingredientes/{id}/         → administrador edita limites Valadares
    - DELETE /api/ingredientes/{id}/        → exclui (só os próprios, não-Valadares)
    """
    serializer_class = IngredienteSerializer

    def get_permissions(self):
        """MODO TESTE: leitura pública e criação livre, com autenticação opcional somente em operações sensíveis."""
        if self.action in ('update', 'partial_update', 'destroy', 'editar', 'preco'):
            return [IsAuthenticated()]
        return [AllowAny()]

    def _perfil_obrigatorio(self):
        """Retorna o perfil atual ou produz um erro de permissão compreensível."""
        try:
            return self.request.user.perfil_usuario
        except Usuario.DoesNotExist as exc:
            raise PermissionDenied(
                'Complete seu perfil antes de alterar ingredientes.'
            ) from exc

    def get_serializer_class(self):
        if self.action == 'preco':
            return AtualizarPrecoCatalogoInputSerializer
        return super().get_serializer_class()

    # Queryset: Valadares (públicos) + ingredientes do usuário logado
    def get_queryset(self):
        """Lista itens públicos e customizados do usuário, aplicando os filtros."""
        user = self.request.user
        perfil = None

        if getattr(user, 'is_authenticated', False):
            try:
                perfil = user.perfil_usuario
            except Usuario.DoesNotExist:
                perfil = None

        if not getattr(user, 'is_authenticated', False):
            qs = Ingrediente.objects.filter(
                Q(fonte_valadares=True) | Q(fonte_valadares=False, usuario__isnull=True)
            )
        elif perfil:
            qs = Ingrediente.objects.filter(
                Q(fonte_valadares=True) | Q(usuario=perfil) | Q(fonte_valadares=False, usuario__isnull=True)
            )
        else:
            qs = Ingrediente.objects.filter(fonte_valadares=True)

        # Filtros via query params
        params = self.request.query_params
        valadares = params.get('valadares', '').strip().lower()
        if valadares == 'true':
            qs = qs.filter(fonte_valadares=True)
        elif valadares == 'false':
            if perfil:
                qs = qs.filter(fonte_valadares=False, usuario=perfil)
            else:
                qs = qs.filter(fonte_valadares=False, usuario__isnull=True)

        classificacao = params.get('classificacao', '').strip()
        if classificacao:
            qs = qs.filter(classificacao=classificacao)

        tipo = params.get('tipo', '').strip()
        if tipo:
            qs = qs.filter(tipo=tipo)

        search = params.get('search', '').strip()
        if search:
            qs = qs.filter(nome__icontains=search)

        # filtro de ordenação para volumoso primeiro e por ordem alfabétoca
        qs = qs.annotate(
            e_volumoso=Case(
                When(classificacao__iexact='volumoso', then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )

        return qs.order_by('e_volumoso', Lower('nome')).select_related('usuario')


    @action(detail=False, methods=['post'])
    def adicionar(self, request):
        """Mantém a rota legada ``/adicionar/`` usando a criação padrão."""
        return self.create(request)

    def perform_create(self, serializer):
        """Associa o ingrediente ao perfil autenticado quando houver, senão grava como custom sem dono."""
        try:
            perfil = self.request.user.perfil_usuario
        except (AttributeError, Usuario.DoesNotExist):
            perfil = None

        serializer.save(
            usuario=perfil,
            fonte_valadares=False,
        )


    # Protege edição/exclusão e mantém a composição Valadares imutável
    def _verificar_propriedade(self, instance, campos_solicitados=None):
        """Autoriza somente administradores a editar limites globais Valadares."""
        if instance.fonte_valadares:
            usuario_admin = (
                self.request.user.is_staff or self.request.user.is_superuser
            )
            somente_limites = (
                campos_solicitados
                and set(campos_solicitados) <= CAMPOS_LIMITES_PARTICIPACAO
            )
            if (
                self.request.method.lower() == 'patch'
                and usuario_admin
                and somente_limites
            ):
                return
            raise PermissionDenied(
                'Somente administradores podem alterar os limites mínimo e '
                'máximo de ingredientes Valadares.'
            )
        if self.request.user.is_staff or self.request.user.is_superuser:
            return
        perfil = self._perfil_obrigatorio()
        if instance.usuario != perfil:
            raise PermissionDenied('Você só pode editar seus próprios ingredientes.')

    def update(self, request, *args, **kwargs):
        """Atualiza a rota padrão com autorização e o contrato parcial da interface."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self._verificar_propriedade(instance, request.data.keys())
        data = self._limpar_campos_vazios_patch(request.data) if partial else request.data
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        """Encaminha PATCH para ``update`` preservando campos vazios como não alteração."""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


    # PUT/PATCH /api/ingredientes/{id}/editar/
    @action(detail=True, methods=['put', 'patch'], url_path='editar')
    def editar(self, request, pk=None):
        """Edita total ou parcialmente um ingrediente customizado permitido."""
        return self.update(request, pk=pk, partial=request.method.lower() == 'patch')

    @staticmethod
    def _limpar_campos_vazios_patch(data):
        """
        Em PATCH, null/"" em campos obrigatorios significa "nao alterar".
        partial=True so ignora campos ausentes; campos enviados como null
        ainda seriam validados e rejeitados pelo serializer.
        """
        dados = data.copy()
        campos_obrigatorios = {
            'classificacao', 'tipo', 'nome', 'ms', 'pb', 'ndt',
            'fdn', 'ee', 'ca', 'p', 'custo_kg',
        }
        for campo in campos_obrigatorios:
            if campo in dados and dados.get(campo) in (None, ''):
                dados.pop(campo)
        return dados

    def perform_destroy(self, instance):
        """Verifica propriedade antes de excluir um ingrediente customizado."""
        self._verificar_propriedade(instance)
        instance.delete()

    # GET /api/ingredientes/meus/
    @action(detail=False, methods=['get'])
    def meus(self, request):
        """Retorna somente os ingredientes customizados do usuário logado."""
        if not getattr(request.user, 'is_authenticated', False):
            return Response([])
        try:
            perfil = request.user.perfil_usuario
        except Usuario.DoesNotExist:
            return Response([])
        qs = Ingrediente.objects.filter(fonte_valadares=False, usuario=perfil)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


    # GET /api/ingredientes/tipos/
    @action(detail=False, methods=['get'])
    def tipos(self, request):
        """Retorna as opções de classificação e tipo disponíveis."""
        return Response({
            'classificacoes': [{'value': v, 'label': l} for v, l in CLASSIFICACAO_CHOICES],
            'tipos':          [{'value': v, 'label': l} for v, l in TIPO_CHOICES],
        })

    # PATCH /api/ingredientes/{id}/preco/
    @action(detail=True, methods=['patch'], url_path='preco')
    def preco(self, request, pk=None):
        """
        PATCH /api/ingredientes/{id}/preco/

        Corpo: {"preco": 1.85}

        preço é editável em QUALQUER ingrediente visível (Valadares incluso), 
        porque o destino é o banco de preços regional do próprio usuário, 
        não o registro compartilhado do Ingrediente. 
        Editar preço nunca modifica a
        composição bromatológica nem a linha do catálogo.
        """
        try:
            perfil = request.user.perfil_usuario
        except Usuario.DoesNotExist:
            return Response(
                {'detail': 'Complete seu perfil antes de definir preços.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ingrediente = get_object_or_404(self.get_queryset(), pk=pk)
        ser = AtualizarPrecoCatalogoInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        novo_preco = ser.validated_data['preco']

        # Obtem registro atual (se houver) para gravar histórico
        registro_antigo = PrecoIngredienteUsuario.objects.filter(
            usuario=perfil, ingrediente=ingrediente
        ).first()
        preco_anterior = registro_antigo.preco_kg_mn if registro_antigo else None

        registro, _ = PrecoIngredienteUsuario.objects.update_or_create(
            usuario=perfil,
            ingrediente=ingrediente,
            defaults={'preco_kg_mn': novo_preco},
        )

        HistoricoPrecoIngrediente.objects.create(
            ingrediente=ingrediente,
            usuario=perfil,
            preco_anterior=preco_anterior,
            preco_novo=novo_preco,
            origem_alteracao=OrigemAlteracaoPrecoChoices.CATALOGO,
        )

        return Response({
            'ingrediente_id': ingrediente.pk,
            'preco_kg_mn':    registro.preco_kg_mn,
            'dt_atualizacao': registro.dt_atualizacao,
        })
