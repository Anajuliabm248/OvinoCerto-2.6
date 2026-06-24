from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q

from accounts.models import Usuario
from .models import Ingrediente
from .serializers import IngredienteSerializer


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
    - GET  /api/ingredientes/{id}/substitutos/?objetivo=custo|pb|fdn
                                             → sugestões de substituição
    - POST /api/ingredientes/               → cria ingrediente custom
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

        return qs.select_related('usuario')


    # Cria ingrediente custom associado ao usuário logado
    def perform_create(self, serializer):
        try:
            perfil = self.request.user.perfil_usuario
        except Usuario.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Complete seu perfil antes de adicionar ingredientes.')
        serializer.save(usuario=perfil, fonte_valadares=False)


    # Protege edição/exclusão: apenas ingredientes custom do próprio usuário
    def _verificar_propriedade(self, instance):
        from rest_framework.exceptions import PermissionDenied
        if instance.fonte_valadares:
            raise PermissionDenied('Ingredientes Valadares não podem ser alterados.')
        try:
            perfil = self.request.user.perfil_usuario
        except Usuario.DoesNotExist:
            raise PermissionDenied('Acesso negado.')
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
        from .models import CLASSIFICACAO_CHOICES, TIPO_CHOICES
        return Response({
            'classificacoes': [{'value': v, 'label': l} for v, l in CLASSIFICACAO_CHOICES],
            'tipos':          [{'value': v, 'label': l} for v, l in TIPO_CHOICES],
        })

    # GET /api/ingredientes/{id}/substitutos/?objetivo=custo|pb|fdn|ndt
    @action(detail=True, methods=['get'])
    def substitutos(self, request, pk=None):
        """
        Sugere substitutos para o ingrediente, rankeados por objetivo:
          - custo  → menor custo_kg
          - pb     → PB mais próximo
          - fdn    → FDN mais próximo
          - ndt    → NDT mais próximo
        """
        ingrediente = self.get_object()
        objetivo = request.query_params.get('objetivo', 'custo').strip().lower()
        limite   = int(request.query_params.get('limite', 5))

        # Candidatos: mesma classificação, exclui o próprio
        try:
            perfil = request.user.perfil_usuario
            candidatos = Ingrediente.objects.filter(
                classificacao=ingrediente.classificacao
            ).filter(
                Q(fonte_valadares=True) | Q(usuario=perfil)
            ).exclude(pk=ingrediente.pk)
        except Usuario.DoesNotExist:
            candidatos = Ingrediente.objects.filter(
                classificacao=ingrediente.classificacao,
                fonte_valadares=True,
            ).exclude(pk=ingrediente.pk)

        if not candidatos.exists():
            return Response([])

        import numpy as np

        vec_ref = ingrediente.to_vetor_nutricional()  # [pb, ndt, fdn, ee, ca, p]

        def distancia(c):
            vec_c = c.to_vetor_nutricional()
            return float(np.linalg.norm(vec_ref - vec_c))

        def score(c):
            if objetivo == 'custo':
                return c.custo_kg
            if objetivo == 'pb':
                return abs(c.pb - ingrediente.pb)
            if objetivo == 'fdn':
                return abs(c.fdn - ingrediente.fdn)
            if objetivo == 'ndt':
                return abs(c.ndt - ingrediente.ndt)
            # default: distância euclidiana
            return distancia(c)

        rankados = sorted(candidatos, key=score)[:limite]

        resultado = []
        for c in rankados:
            resultado.append({
                'ingrediente':          IngredienteSerializer(c).data,
                'delta_custo':          round(c.custo_kg - ingrediente.custo_kg, 4),
                'delta_pb':             round(c.pb - ingrediente.pb, 4),
                'delta_ndt':            round(c.ndt - ingrediente.ndt, 4),
                'delta_fdn':            round(c.fdn - ingrediente.fdn, 4),
                'distancia_euclidiana': round(distancia(c), 6),
            })

        return Response(resultado)