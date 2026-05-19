from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.index, name='index'),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('perfil/', views.editar_perfil, name='perfil'),
    path('usuarios/', views.usuarios, name='usuarios'),
    path('usuarios/novo/', views.usuario_criar, name='usuario_criar'),
    path('usuarios/<int:user_id>/editar/', views.usuario_editar, name='usuario_editar'),
    path('usuarios/<int:user_id>/excluir/', views.usuario_excluir, name='usuario_excluir'),
]
