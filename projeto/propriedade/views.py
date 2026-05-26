from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from accounts.models import Usuario

from .forms import PropriedadeForm
from .models import Propriedade


def perfil_do_usuario(user):
    try:
        return user.perfil_usuario
    except Usuario.DoesNotExist:
        return None


def propriedades_do_usuario(user):
    propriedades = Propriedade.objects.select_related('usuario', 'usuario__user')

    if user.is_superuser:
        return propriedades.order_by('nome')

    perfil_usuario = perfil_do_usuario(user)
    if perfil_usuario is None:
        return propriedades.none()

    return propriedades.filter(usuario=perfil_usuario).order_by('nome')


@login_required
def listar(request):
    busca = request.GET.get('busca', '').strip()
    propriedades = propriedades_do_usuario(request.user)

    if busca:
        propriedades = propriedades.filter(
            Q(nome__icontains=busca)
            | Q(cnpj__icontains=busca)
            | Q(proprietario__icontains=busca)
            | Q(telefone__icontains=busca)
            | Q(uf__icontains=busca)
            | Q(cidade__icontains=busca)
            | Q(localidade__icontains=busca)
        )

    paginator = Paginator(propriedades, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'title': 'Propriedades',
        'page_obj': page_obj,
        'busca': busca,
    }
    return render(request, 'global/propriedade/propriedades.html', context)


@login_required
def busca_propriedades(request):
    return listar(request)


@login_required
@require_http_methods(['GET', 'POST'])
def cadastro_propriedade(request):
    perfil_usuario = perfil_do_usuario(request.user)
    if perfil_usuario is None:
        messages.error(request, 'Complete seu perfil antes de cadastrar uma propriedade.')
        return redirect('accounts:perfil')

    form = PropriedadeForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        propriedade = form.save(commit=False)
        propriedade.usuario = perfil_usuario
        propriedade.save()
        messages.success(request, 'Propriedade cadastrada com sucesso.')
        return redirect('propriedade:listar')

    return render(
        request,
        'global/propriedade/cadastro.html',
        {
            'title': 'Cadastro',
            'form': form,
        },
    )


@login_required
@require_http_methods(['GET', 'POST'])
def editar_propriedade(request, propriedade_id):
    propriedade = get_object_or_404(
        propriedades_do_usuario(request.user),
        id=propriedade_id,
    )
    form = PropriedadeForm(request.POST or None, instance=propriedade)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Propriedade editada com sucesso.')
        return redirect('propriedade:listar')

    return render(
        request,
        'global/propriedade/editar_propriedade.html',
        {
            'form': form,
            'title': 'Editar Propriedade',
        },
    )


@login_required
@require_http_methods(['GET', 'POST'])
def excluir_propriedade(request, propriedade_id):
    propriedade = get_object_or_404(
        propriedades_do_usuario(request.user),
        id=propriedade_id,
    )

    if request.method == 'POST':
        propriedade.delete()
        messages.success(request, 'Propriedade excluida com sucesso.')
        return redirect('propriedade:listar')

    return render(
        request,
        'global/propriedade/propriedade_confirm_delete.html',
        {
            'title': 'Excluir Propriedade',
            'propriedade': propriedade,
            'cancelar_url': reverse('propriedade:listar'),
        },
    )
