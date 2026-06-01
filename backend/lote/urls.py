from django.urls import path
from . import views

app_name = 'lote'

urlpatterns = [
    path('<int:propriedade_id>/', views.listar, name='listar'),
    path('<int:propriedade_id>/cadastrar/', views.cadastrar, name='cadastrar'),
    path('<int:lote_id>/editar/', views.editar, name='editar'),
    path('<int:lote_id>/excluir/', views.excluir, name='excluir'),
]