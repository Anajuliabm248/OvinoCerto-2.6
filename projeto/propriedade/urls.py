from django.urls import path
from . import views

app_name = 'propriedade'

urlpatterns = [
    path('', views.listar, name='listar'),
    path('cadastrar/', views.cadastro_propriedade, name='cadastrar'),
    path('<int:propriedade_id>/editar/', views.editar_propriedade, name='editar'),
    path('<int:propriedade_id>/excluir/', views.excluir_propriedade, name='excluir'),
]
