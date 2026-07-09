"""
Listagem de ingredientes disponíveis para seleção em uma formulação.

Ordenação (seção 2.7 / 15 do documento de arquitetura):
  1. Classe nutricional: VOLUMOSO antes de CONCENTRADO (ordem explícita,
     não alfabética — 'concentrado' < 'volumoso' alfabeticamente, por
     isso usamos Case/When para forçar a ordem correta).
  2. Tipo (dentro da classe).
  3. Nome.

Ingredientes do sistema (fonte_valadares=True) e personalizados do
usuário (fonte_valadares=False, usuario=request.user) são mesclados
na mesma listagem — sem separação visual por origem (regra de
negócio: tratamento funcionalmente idêntico no motor).
"""

from __future__ import annotations

from django.db.models import Case, IntegerField, Q, When

from ingrediente.models import Ingrediente

ORDEM_CLASSIFICACAO = Case(
    When(classificacao="volumoso", then=1),
    When(classificacao="concentrado", then=2),
    default=3,
    output_field=IntegerField(),
)


def listar_ingredientes_disponiveis(usuario_id: int | None):
    """
    Retorna queryset de Ingrediente visível para o usuário:
    - todos os ingredientes do sistema (fonte_valadares=True)
    - ingredientes customizados do próprio usuário (usuario_id=usuario_id)

    Ordenado: volumoso → concentrado, depois tipo, depois nome.

    Se usuario_id for None (usuário sem perfil), retorna apenas os do
    sistema — sem tentar filtrar por usuario_id=None, o que produziria
    Q(usuario_id__isnull=True) e poderia trazer ingredientes órfãos.
    """
    filtro = Q(fonte_valadares=True)
    if usuario_id is not None:
        filtro |= Q(usuario_id=usuario_id)

    return (
        Ingrediente.objects
        .filter(filtro)
        .annotate(_ordem_classe=ORDEM_CLASSIFICACAO)
        .order_by("_ordem_classe", "tipo", "nome")
    )