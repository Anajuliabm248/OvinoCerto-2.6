from rest_framework.routers import DefaultRouter

from formulacao.api.viewsets import FormulacaoViewSet

router = DefaultRouter()
router.register(r"formulacoes", FormulacaoViewSet, basename="formulacao")

urlpatterns = router.urls