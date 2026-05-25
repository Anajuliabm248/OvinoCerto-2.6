from importlib.resources import path
from django.urls import include
from rest_framework import DefaultRouter
from .views import PropriedadeViewSet

router = DefaultRouter()
router.register(r'propriedades', PropriedadeViewSet, basename='propriedade')

# as URLs do viewset são automaticamente geradas pelo router
urlpatterns = [
    path('propriedades/', include(router.urls)),
]