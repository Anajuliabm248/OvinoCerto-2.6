from django.shortcuts import render
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Propriedade
from .serializers import PropriedadeSerializer

# Create your views here.

class PropriedadeViewSet(viewsets.ModelViewSet):
    serializer_class = PropriedadeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # se for adm pode ver todas as propriedades, caso contrário só as suas
        if user.admin:
            return Propriedade.objects.all()
        return Propriedade.objects.filter(usuario=user)

    def perform_create(self, serializer):
        # liga o usuário autenticado à propriedade criada
        serializer.save(usuario=self.request.user)
        
    def perform_update(self, serializer):
        # só permite atualizar se for o dono da propriedade (adm não pode editar, mas vou perguntar sobre isso depois)
        instance = self.get_object()
        user = self.request.user
        if instance.usuario != user:
            raise PermissionDenied("Você não tem permissão para editar esta propriedade.")
        serializer.save()
        
    def perform_destroy(self, instance):
        # só permite deletar se for o dono da propriedade
        user = self.request.user
        if instance.usuario != user:
            raise PermissionDenied("Você não tem permissão para deletar esta propriedade.")
        instance.delete()
        
    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if not user.admin and obj.usuario != user:
            raise PermissionDenied("Você não tem permissão para acessar esta propriedade.")
        return obj