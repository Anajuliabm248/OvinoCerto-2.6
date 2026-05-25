from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Lote
from .serializers import LoteSerializer

# Create your views here.

class LoteViewSet(viewsets.ModelViewSet):
    serializer_class = LoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # se for admin pode ver todos lotes, senão apenas os seus
        if user.admin:
            pass
        else:
            qs = qs.filter(propriedade__usuario=user)
            
        propriedade_id = self.request.query_params.get('propriedade')
        
        if propriedade_id:
            qs = qs.filter(propriedade_id=propriedade_id)
            
        return qs
    
    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if not user.admin and obj.propriedade.usuario != user:
            raise PermissionDenied("Você não tem permissão para acessar este lote.")
        return obj
    