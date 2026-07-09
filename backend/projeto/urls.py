"""urls do projeto Django"""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from accounts.viewsets import UsuarioViewSet, RegisterView, LoginView
from formulacao.api.viewsets import FormulacaoViewSet
from propriedade.viewsets import PropriedadeViewSet
from lote.viewsets import LoteViewSet
from exigencia_nrc.viewsets import ExigenciaNRCViewSet
from ingrediente.viewsets import IngredienteViewSet

router = DefaultRouter()
router.register(r'usuarios',    UsuarioViewSet,      basename='usuario')
router.register(r'propriedades', PropriedadeViewSet, basename='propriedade')
router.register(r'lotes',        LoteViewSet,        basename='lote')
router.register(r'exigencias',   ExigenciaNRCViewSet, basename='exigencia')
router.register(r'ingredientes', IngredienteViewSet,  basename='ingrediente')
router.register(r'formulacao', FormulacaoViewSet, basename='formulacao')

urlpatterns = [
    # Admin Django
    path('admin/', admin.site.urls),

    # Autenticação JWT
    path('api/auth/login/',   LoginView.as_view(),      name='auth-login'),
    path('api/auth/register/', RegisterView.as_view(),  name='auth-register'),
    path('api/auth/refresh/',  TokenRefreshView.as_view(), name='auth-refresh'),

    # API REST
    path('api/', include(router.urls)),

    # Browser API (login do DRF browsable)
    path('api-auth/', include('rest_framework.urls')),

    # drf-spectacular
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'),
         name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

urlpatterns += static(settings.MEDIA_URL,  document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
