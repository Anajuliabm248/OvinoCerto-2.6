from .models import Usuario


def usuario_admin(request):
    user = getattr(request, 'user', None)
    pode_gerenciar = False

    if user and user.is_authenticated:
        if user.is_staff or user.is_superuser:
            pode_gerenciar = True
        else:
            try:
                pode_gerenciar = user.perfil_usuario.pode_gerenciar_usuarios
            except Usuario.DoesNotExist:
                pode_gerenciar = False

    return {
        'usuario_pode_gerenciar_usuarios': pode_gerenciar,
    }
