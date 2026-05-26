from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from propriedade.models import Propriedade

from .forms import LoteForm
from .models import Lote


def _get_propriedade_do_usuario(user, propriedade_id):
    """Retorna a propriedade se pertencer ao usuário (ou se superuser)."""
    qs = Propriedade.objects.select_related('usuario')
    if user.is_superuser:
        return get_object_or_404(qs, id=propriedade_id)
    return get_object_or_404(qs, id=propriedade_id, usuario=user)


@login_required
def listar(request, propriedade_id):
    propriedade = _get_propriedade_do_usuario(request.user, propriedade_id)
    busca = request.GET.get('busca', '').strip()

    lotes = Lote.objects.filter(propriedade=propriedade)
    if busca:
        lotes = lotes.filter(
            Q(nome_lote__icontains=busca)
            | Q(raca__icontains=busca)
            | Q(sistema__icontains=busca)
            | Q(categoria__icontains=busca)
            | Q(fase__icontains=busca)
        )

    paginator = Paginator(lotes, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'global/lote/lotes.html', {
        'title': f'Lotes — {propriedade.nome}',
        'propriedade': propriedade,
        'page_obj': page_obj,
        'busca': busca,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def cadastrar(request, propriedade_id):
    propriedade = _get_propriedade_do_usuario(request.user, propriedade_id)
    form = LoteForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        lote = form.save(commit=False)
        lote.propriedade = propriedade
        lote.save()
        messages.success(request, 'Lote cadastrado com sucesso.')
        return redirect('lote:listar', propriedade_id=propriedade.id)

    return render(request, 'global/lote/cadastro_lote.html', {
        'title': 'Cadastrar Lote',
        'propriedade': propriedade,
        'form': form,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def editar(request, lote_id):
    lote = get_object_or_404(Lote, id=lote_id)
    # Garante que o lote pertence a uma propriedade do usuário
    _get_propriedade_do_usuario(request.user, lote.propriedade_id)

    form = LoteForm(request.POST or None, instance=lote)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Lote editado com sucesso.')
        return redirect('lote:listar', propriedade_id=lote.propriedade_id)

    return render(request, 'global/lote/editar_lote.html', {
        'title': 'Editar Lote',
        'propriedade': lote.propriedade,
        'form': form,
        'lote': lote,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def excluir(request, lote_id):
    lote = get_object_or_404(Lote, id=lote_id)
    _get_propriedade_do_usuario(request.user, lote.propriedade_id)

    if request.method == 'POST':
        propriedade_id = lote.propriedade_id
        lote.delete()
        messages.success(request, 'Lote excluído com sucesso.')
        return redirect('lote:listar', propriedade_id=propriedade_id)

    return render(request, 'global/lote/lote_confirm_delete.html', {
        'title': 'Excluir Lote',
        'lote': lote,
        'propriedade': lote.propriedade,
        'cancelar_url': reverse('lote:listar', kwargs={'propriedade_id': lote.propriedade_id}),
    })