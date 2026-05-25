from django.urls import include, path
from rest_framework import DefaultRouter
from .views import LoteViewSet

router = DefaultRouter()
router.register(r'lotes', LoteViewSet, basename='lote')

urlpatterns = [
    path('lotes/', include(router.urls)),
]