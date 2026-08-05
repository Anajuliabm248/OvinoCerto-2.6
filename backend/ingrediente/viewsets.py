"""viewsets do app de ingredientes"""

from email.policy import default

from django.forms.fields import IntegerField
import numpy as np

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q, Case, When, Value, IntegerField
from django.shortcuts import get_object_or_404
from django.db.models.functions import Lower

from accounts.models import Usuario
from .models import (
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
    - PUT/PATCH /api/ingredientes/{id}/     → edita (só os próprios, não-Valadares)
    - DELETE /api/ingredientes/{id}/        → exclui (só os próprios, não-Valadares)
    """
    serializer_class = IngredienteSerializer
    permission_classes = [IsAuthenticated]

    # Queryset: Valadares (públicos) + ingredientes do usuário logado
    def get_queryset(self):
        user = self.request.user

        try:
            perfil = user.perfil_usuario
        except Usuario.DoesNotExist:
            perfil = None

        if perfil:
            qs = Ingrediente.objects.filter(
                Q(fonte_valadares=True) | Q(usuario=perfil)
            )
        else:
            qs = Ingrediente.objects.filter(fonte_valadares=True)

        # Filtros via query params
        params = self.request.query_params
        valadares = params.get('valadares', '').strip().lower()
        if valadares == 'true':
            qs = qs.filter(fonte_valadares=True)
        elif valadares == 'false' and perfil:
            qs = qs.filter(fonte_valadares=False, usuario=perfil)

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


    # Cria ingrediente custom associado ao usuário logado
    def perform_create(self, serializer):
        try:
            perfil = self.request.user.perfil_usuario
        except Usuario.DoesNotExist as exc:
            raise PermissionDenied('Complete seu perfil antes de adicionar ingredientes.') from exc
        serializer.save(usuario=perfil, fonte_valadares=False)

    # Protege edição/exclusão: apenas ingredientes custom do próprio usuário
    def _verificar_propriedade(self, instance):
        '''Verifica se o usuário tem permissão para editar/excluir o ingrediente'''
        if instance.fonte_valadares:
            raise PermissionDenied('Ingredientes Valadares não podem ser alterados.')
        try:
            perfil = self.request.user.perfil_usuario
        except Usuario.DoesNotExist as exc:
            raise PermissionDenied('Acesso negado.') from exc
        if instance.usuario != perfil and not self.request.user.is_staff:
            raise PermissionDenied('Você só pode editar seus próprios ingredientes.')

    def perform_update(self, serializer):
        self._verificar_propriedade(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._verificar_propriedade(instance)
        instance.delete()

    # GET /api/ingredientes/meus/
    @action(detail=False, methods=['get'])
    def meus(self, request):
        """Retorna somente os ingredientes customizados do usuário logado."""
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

        registro, created = PrecoIngredienteUsuario.objects.update_or_create(
            usuario=perfil,
            ingrediente=ingrediente,
            defaults={'preco_kg_mn': novo_preco},
        )

        # Grava histórico da alteração (origem = CATALOGO)
        try:
            origem = OrigemAlteracaoPrecoChoices.CATALOGO
        except Exception:
            origem = 'CATALOGO'

        HistoricoPrecoIngrediente.objects.create(
            ingrediente=ingrediente,
            usuario=perfil,
            preco_anterior=preco_anterior,
            preco_novo=novo_preco,
            origem_alteracao=origem,
        )

        return Response({
            'ingrediente_id': ingrediente.pk,
            'preco_kg_mn':    registro.preco_kg_mn,
            'dt_atualizacao': registro.dt_atualizacao,
        })
    