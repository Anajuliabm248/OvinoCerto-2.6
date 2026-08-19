"""ViewSet para a tabela NRC de exigências nutricionais"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from lote.models import FASES_COM_PARTO_E_DIAS, CATEGORIA_CHOICES
from .models import ExigenciaNRC
from .serializers import ExigenciaNRCSerializer


# pylint: disable= no-member, unused-argument, too-many-branches, too-many-ancestors

class ExigenciaNRCViewSet(viewsets.ModelViewSet):
    """
    Tabela NRC de exigências nutricionais.

    - GET  /api/exigencias/                  → lista todas
    - GET  /api/exigencias/{id}/             → detalhe
    - GET  /api/exigencias/categorias/       → lista valores únicos de categoria
    - GET  /api/exigencias/lookup/           → busca a linha mais próxima
    - POST/PUT/DELETE                        → somente admin
    """
    serializer_class = ExigenciaNRCSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return [AllowAny()]

    def get_queryset(self):
        qs = ExigenciaNRC.objects.all()

        categoria = self.request.query_params.get('categoria', '')
        fase      = self.request.query_params.get('fase', '')
        if categoria:
            qs = qs.filter(categoria=categoria)
        if fase:
            qs = qs.filter(fase=fase)
        return qs

    @action(detail=False, methods=['get'])
    def categorias(self, request):
        """Retorna lista de categorias distintas presentes na tabela NRC."""
        cats = (
            ExigenciaNRC.objects
            .values_list('categoria', flat=True)
            .distinct()
            .order_by('categoria')
        )
        label_map = dict(CATEGORIA_CHOICES)
        return Response([
            {'value': c, 'label': label_map.get(c, c)}
            for c in cats
        ])

    @action(detail=False, methods=['get'])
    def lookup(self, request):
        """
        Retorna a exigência NRC mais adequada para os parâmetros fornecidos.

        Parâmetros obrigatórios: categoria, fase, pv_kg
        Parâmetros opcionais:    gmd (kg/dia), tipo_parto (1–5)
        """
        categoria   = request.query_params.get('categoria', '').strip()
        fase        = request.query_params.get('fase', '').strip()
        pv_kg_str   = request.query_params.get('pv_kg', '').strip()
        gmd_str     = request.query_params.get('gmd', '').strip()
        tipo_parto  = request.query_params.get('tipo_parto', '').strip()

        # Validação básica
        erros = {}
        if not categoria:
            erros['categoria'] = 'Obrigatório.'
        if not fase:
            erros['fase'] = 'Obrigatório.'
        if not pv_kg_str:
            erros['pv_kg'] = 'Obrigatório.'
        if erros:
            return Response(erros, status=status.HTTP_400_BAD_REQUEST)

        try:
            pv_kg = float(pv_kg_str)
        except ValueError:
            return Response({'pv_kg': 'Deve ser um número.'}, status=status.HTTP_400_BAD_REQUEST)

        gmd = None
        if gmd_str:
            try:
                gmd = float(gmd_str)
            except ValueError:
                return Response({'gmd': 'Deve ser um número.'}, status=status.HTTP_400_BAD_REQUEST)

        # Filtro base: categoria + fase
        qs = ExigenciaNRC.objects.filter(categoria=categoria, fase=fase)

        # Tipo de parto (fases de gestação / lactação)
        if fase in FASES_COM_PARTO_E_DIAS:
            if tipo_parto:
                try:
                    qs = qs.filter(tipo_parto=int(tipo_parto))
                except ValueError:
                    pass

        if not qs.exists():
            return Response(
                {'detail': 'Nenhuma exigência NRC encontrada para esta combinação.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Escolhe pelo pv_kg mais próximo
        best = min(qs, key=lambda e: abs((e.pv_kg or 0) - pv_kg))

        # Se há empate em pv_kg e gmd foi fornecido, desempata pelo gmd
        if gmd is not None:
            mesmo_pv = [e for e in qs if e.pv_kg == best.pv_kg]
            if len(mesmo_pv) > 1:
                best = min(mesmo_pv, key=lambda e: abs((e.gmd_kg or 0) - gmd))

        return Response(ExigenciaNRCSerializer(best).data)
