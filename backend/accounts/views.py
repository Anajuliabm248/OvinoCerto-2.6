from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from .forms import (
    AdminUsuarioForm,
    CadastroUsuarioForm,
    LoginUsuarioForm,
    PerfilUsuarioForm,
)
from .models import Usuario


User = get_user_model()


def usuario_pode_gerenciar(user):
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    try:
        return user.perfil_usuario.pode_gerenciar_usuarios
    except Usuario.DoesNotExist:
        return False


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not usuario_pode_gerenciar(request.user):
            messages.error(request, 'Voce nao tem permissao para gerenciar usuarios.')
            return redirect('accounts:index')
        return view_func(request, *args, **kwargs)

    return wrapper

#evita ataques de tipo “open redirect”, garantindo que a URL de redirecionamento seja segura e pertença ao mesmo domínio do site.
def redirect_seguro(request, fallback='accounts:index'):
    proxima_url = request.POST.get('next') or request.GET.get('next')
    if proxima_url and url_has_allowed_host_and_scheme(
        proxima_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(proxima_url)
    return redirect(fallback)


def index(request):
    context = {
        'title': 'Home',
    }
    return render(request, 'global/accounts/index.html', context)


@require_http_methods(['GET', 'POST'])
def cadastro(request):
    if request.user.is_authenticated:
        return redirect('accounts:index')

    form = CadastroUsuarioForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        auth_login(request, user)
        messages.success(request, 'Cadastro realizado com sucesso.')
        return redirect('accounts:index')

    return render(
        request,
        'global/accounts/cadastro.html',
        {
            'title': 'Cadastro',
            'form': form,
        },
    )


@require_http_methods(['GET', 'POST'])
def login(request):
    if request.user.is_authenticated:
        return redirect('accounts:index')

    form = LoginUsuarioForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        auth_login(request, form.user)
        messages.success(request, 'Login realizado com sucesso.')
        return redirect_seguro(request)

    return render(
        request,
        'global/accounts/login.html',
        {
            'title': 'Login',
            'form': form,
            'next': request.GET.get('next', ''),
        },
    )


@login_required
@require_POST
def logout(request):
    auth_logout(request)
    messages.success(request, 'Voce saiu da sua conta.')
    return redirect('accounts:login')


@login_required
@require_http_methods(['GET', 'POST'])
def editar_perfil(request):
    try:
        perfil_usuario = request.user.perfil_usuario
    except Usuario.DoesNotExist:
        perfil_usuario = None

    form = PerfilUsuarioForm(
        request.POST or None,
        user_instance=request.user,
        perfil_instance=perfil_usuario,
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Perfil atualizado com sucesso.')
        return redirect('accounts:perfil')

    return render(
        request,
        'global/accounts/perfil.html',
        {
            'title': 'Editar perfil',
            'form': form,
        },
    )


@admin_required
def usuarios(request):
    busca = request.GET.get('busca', '').strip()
    usuarios_qs = User.objects.select_related('perfil_usuario').order_by('first_name', 'username')

    if busca:
        usuarios_qs = usuarios_qs.filter(
            Q(first_name__icontains=busca)
            | Q(username__icontains=busca)
            | Q(email__icontains=busca)
            | Q(perfil_usuario__nome__icontains=busca)
            | Q(perfil_usuario__email__icontains=busca)
            | Q(perfil_usuario__cpf__icontains=busca)
        )

    return render(
        request,
        'global/accounts/usuarios.html',
        {
            'title': 'Usuarios',
            'usuarios': usuarios_qs,
            'busca': busca,
        },
    )


@admin_required
@require_http_methods(['GET', 'POST'])
def usuario_criar(request):
    form = AdminUsuarioForm(request.POST or None, actor=request.user)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Usuario criado com sucesso.')
        return redirect('accounts:usuarios')

    return render(
        request,
        'global/accounts/usuario_form.html',
        {
            'title': 'Novo usuario',
            'form': form,
            'acao': 'Criar usuario',
        },
    )


@admin_required
@require_http_methods(['GET', 'POST'])
def usuario_editar(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)

    if usuario.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Apenas superusuarios podem editar outro superusuario.')
        return redirect('accounts:usuarios')

    try:
        perfil_usuario = usuario.perfil_usuario
    except Usuario.DoesNotExist:
        perfil_usuario = None

    form = AdminUsuarioForm(
        request.POST or None,
        actor=request.user,
        user_instance=usuario,
        perfil_instance=perfil_usuario,
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Usuario atualizado com sucesso.')
        return redirect('accounts:usuarios')

    return render(
        request,
        'global/accounts/usuario_form.html',
        {
            'title': 'Editar usuario',
            'form': form,
            'acao': 'Salvar usuario',
            'usuario_editado': usuario,
        },
    )


@admin_required
@require_http_methods(['GET', 'POST'])
def usuario_excluir(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)

    if usuario.pk == request.user.pk:
        messages.error(request, 'Voce nao pode excluir o proprio usuario.')
        return redirect('accounts:usuarios')
    if usuario.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Apenas superusuarios podem excluir outro superusuario.')
        return redirect('accounts:usuarios')

    if request.method == 'POST':
        usuario.delete()
        messages.success(request, 'Usuario excluido com sucesso.')
        return redirect('accounts:usuarios')

    return render(
        request,
        'global/accounts/usuario_confirm_delete.html',
        {
            'title': 'Excluir usuario',
            'usuario_editado': usuario,
            'cancelar_url': reverse('accounts:usuarios'),
        },
    )
