"""Roteador isolado da formulação, útil quando o app é incluído separadamente."""

from rest_framework.routers import DefaultRouter

from formulacao.api.viewsets import FormulacaoViewSet

router = DefaultRouter()
router.register(r"formulacoes", FormulacaoViewSet, basename="formulacao")

urlpatterns = router.urls
"""Rotas legadas do app; o roteamento principal fica em ``projeto.urls``."""
