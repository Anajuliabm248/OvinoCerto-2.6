"""
Listagem de ingredientes disponíveis para seleção em uma formulação.

Dois modos de ordenação, mutuamente exclusivos:

  Padrão (ordenar_por_preco=None)
    Ordenação por classe → tipo → nome, com regras de negócio:
      1. Classe nutricional: VOLUMOSO antes de CONCENTRADO (ordem
         explícita, não alfabética — 'concentrado' < 'volumoso'
         alfabeticamente, por isso usamos Case/When).
      2. Tipo (dentro da classe).
      3. Nome.

  Por preço (ordenar_por_preco="asc" | "desc")
    Ordenação por Ingrediente.custo_kg, crescente ou decrescente.
    Regra de negócio: ingredientes SEM preço
    informado (custo_kg null OU 0.0) NUNCA aparecem no topo — vão
    sempre para o final da lista, independente da direção escolhida,
    sinalizados por `_sem_preco=True`. Dentro do próprio grupo "sem
    preço", a ordenação cai para nome (não há preço para comparar).

`_sem_preco` é sempre anotado, mesmo na ordenação padrão — o
serializer usa essa anotação para expor o flag "preço não informado"
ao front independentemente do modo de ordenação ativo.

Ingredientes do sistema (fonte_valadares=True) e personalizados do
usuário (fonte_valadares=False, usuario=request.user) são mesclados
na mesma listagem — sem separação visual por origem (regra de
negócio: tratamento funcionalmente idêntico no motor).
"""

from __future__ import annotations

from django.db.models import Case, F, IntegerField, Q, When

from ingrediente.models import Ingrediente

ORDEM_CLASSIFICACAO = Case(
    When(classificacao="volumoso", then=1),
    When(classificacao="concentrado", then=2),
    default=3,
    output_field=IntegerField(),
)

FLAG_SEM_PRECO = Case(
    When(Q(custo_kg__isnull=True) | Q(custo_kg=0), then=1),
    default=0,
    output_field=IntegerField(),
)


def listar_ingredientes_disponiveis(
    usuario_id: int | None,
    ordenar_por_preco: str | None = None,
):
    """
    Retorna queryset de Ingrediente visível para o usuário:
    - todos os ingredientes do sistema (fonte_valadares=True)
    - ingredientes customizados do próprio usuário (usuario_id=usuario_id)

    Parâmetros
    ----------
    usuario_id        : perfil do usuário logado. Se None (sem perfil),
                        retorna apenas ingredientes do sistema — sem
                        filtrar por usuario_id=None, o que produziria
                        Q(usuario_id__isnull=True) e traria órfãos.
    ordenar_por_preco : None (padrão: classe→tipo→nome) | "asc" | "desc".
                        Qualquer valor fora desse conjunto é tratado
                        como None (fallback seguro, não gera erro).
    """
    filtro = Q(fonte_valadares=True)
    if usuario_id is not None:
        filtro |= Q(usuario_id=usuario_id)

    qs = (
        Ingrediente.objects
        .filter(filtro)
        .annotate(_sem_preco=FLAG_SEM_PRECO)
    )

    if ordenar_por_preco in ("asc", "desc"):
        campo_preco = (
            F("custo_kg").asc() if ordenar_por_preco == "asc" else F("custo_kg").desc()
        )
        return qs.order_by("_sem_preco", campo_preco, "nome")

    return (
        qs
        .annotate(_ordem_classe=ORDEM_CLASSIFICACAO)
        .order_by("_ordem_classe", "tipo", "nome")
    )
