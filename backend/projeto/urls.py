from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
from django.conf import settings
from rest_framework.routers import DefaultRouter

from accounts.viewsets import UsuarioViewSet
from propriedade.viewsets import PropriedadeViewSet
from lote.viewsets import LoteViewSet

# Criar router para as APIs
router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuario')
router.register(r'propriedades', PropriedadeViewSet, basename='propriedade')
router.register(r'lotes', LoteViewSet, basename='lote')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    # URLs tradicionais (manter para compatibilidade)
    path('', include('accounts.urls')),
    path('propriedade/', include('propriedade.urls')),
    path('lote/', include('lote.urls')),
]  

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
