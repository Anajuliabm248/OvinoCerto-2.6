"""
Serializers DRF para o módulo de formulação.

Responsabilidade única: tradução HTTP <-> DTOs.

NOTA DE BUGS CORRIGIDOS
-----------------------
PrimaryKeyRelatedField com `source=` fazia validated_data usar o nome
da source como chave (ex.: "lote" em vez de "lote_id"), quebrando o
acesso no viewset. Removemos `source=` de todos os campos de PK —
validated_data agora usa o nome do campo e retorna a instância do
model; o viewset chama .pk explicitamente onde o service espera int.

Todos os serializers de entrada agora recebem context para que os
querysets dinâmicos (lotes do usuário, ingredientes disponíveis) sejam
filtrados corretamente na API navegável do DRF.
"""

from django.db.models import Q
from rest_framework import serializers

from exigencia_nrc.models import ExigenciaNRC
from formulacao.models import (
    Alerta,
    ConfiguracaoNutriente,
    EventoFormulacao,
    Formulacao,
    IngredienteFormulacao,
    SnapshotFormulacao,
)
from ingrediente.models import Ingrediente
from lote.models import Lote


# ---------------------------------------------------------------------------
# Helpers de contexto (usados em __init__ dos serializers de entrada)
# ---------------------------------------------------------------------------

def _perfil(context):
    req = context.get("request")
    return getattr(req.user, "perfil_usuario", None) if req else None


def _lotes_do_usuario(context):
    req = context.get("request")
    if not req:
        return Lote.objects.none()
    qs = Lote.objects.select_related("propriedade__usuario")
    if req.user.is_staff or req.user.is_superuser:
        return qs
    perfil = _perfil(context)
    return qs.filter(propriedade__usuario=perfil) if perfil else Lote.objects.none()


def _ingredientes_do_usuario(context):
    req = context.get("request")
    if not req:
        return Ingrediente.objects.filter(fonte_valadares=True)
    perfil = _perfil(context)
    if perfil is None:
        return Ingrediente.objects.filter(fonte_valadares=True)
    return (
        Ingrediente.objects
        .filter(Q(fonte_valadares=True) | Q(usuario=perfil))
        .order_by("classificacao", "tipo", "nome")
    )


# ---------------------------------------------------------------------------
# Exigências NRC (seleção pelo usuário antes de iniciar)
# ---------------------------------------------------------------------------

class ExigenciaNRCSerializer(serializers.ModelSerializer):
    categoria_display = serializers.CharField(source="get_categoria_display", read_only=True)
    fase_display      = serializers.CharField(source="get_fase_display",      read_only=True)

    class Meta:
        model = ExigenciaNRC
        fields = [
            "id", "categoria", "categoria_display", "fase", "fase_display",
            "pv_kg", "tipo_parto", "dias_fase", "gmd_kg", "cms_kg",
            "pb_percentual", "ndt_percentual", "fdn_percentual",
            "ee_percentual", "ca_percentual", "p_percentual", "ca_p_percentual",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Ingredientes disponíveis (listagem)
# ---------------------------------------------------------------------------

class IngredienteDisponivelSerializer(serializers.Serializer):
    id              = serializers.IntegerField()
    nome            = serializers.CharField()
    classificacao   = serializers.CharField()
    tipo            = serializers.CharField()
    ms              = serializers.FloatField()
    pb              = serializers.FloatField()
    ndt             = serializers.FloatField()
    fdn             = serializers.FloatField()
    ee              = serializers.FloatField()
    ca              = serializers.FloatField()
    p               = serializers.FloatField()
    custo_kg        = serializers.FloatField()
    fonte_valadares = serializers.BooleanField()


# ---------------------------------------------------------------------------
# Criação — etapa 1: iniciar
# ---------------------------------------------------------------------------

class IniciarFormulacaoInputSerializer(serializers.Serializer):
    """
    lote_id e exigencia_nrc_id retornam instâncias do model —
    chame .pk no viewset ao passar para o service.
    """
    lote_id = serializers.PrimaryKeyRelatedField(
        queryset=Lote.objects.none(),
        label="Lote",
        help_text="Escolha um dos seus lotes.",
    )
    exigencia_nrc_id = serializers.PrimaryKeyRelatedField(
        queryset=ExigenciaNRC.objects.all().order_by("categoria", "fase", "pv_kg", "gmd_kg"),
        label="Exigência NRC",
        help_text="ID da ExigenciaNRC escolhida na listagem sugerida.",
    )
    titulo      = serializers.CharField(max_length=200, label="Título")
    observacoes = serializers.CharField(
        required=False, allow_blank=True, default="", label="Observações"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lote_id"].queryset = _lotes_do_usuario(self.context)


# ---------------------------------------------------------------------------
# Criação — etapa 2: gerar distribuição inicial
# ---------------------------------------------------------------------------

class GerarFormulacaoInicialInputSerializer(serializers.Serializer):
    """
    ingrediente_ids retorna lista de instâncias Ingrediente —
    use [i.pk for i in validated_data["ingrediente_ids"]] no viewset.
    """
    ingrediente_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Ingrediente.objects.none(),
        label="Ingredientes",
        help_text="Selecione um ou mais ingredientes para gerar a formulação inicial.",
    )
    percentual_alvo_volumoso = serializers.FloatField(
        required=False,
        default=0.50,
        min_value=0.0,
        max_value=1.0,
        label="% alvo volumosos (0-1)",
        help_text="Fração-alvo de volumosos na distribuição heurística. Padrão 0.50.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ingrediente_ids"].queryset = _ingredientes_do_usuario(self.context)


# ---------------------------------------------------------------------------
# Exigência configurada
# ---------------------------------------------------------------------------

class ConfiguracaoNutrienteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ConfiguracaoNutriente
        fields = [
            "id", "nutriente", "operador", "valor_min", "valor_max",
            "valor_origem_nrc", "alterado_pelo_usuario", "dt_alteracao",
        ]
        read_only_fields = fields


class AtualizarExigenciaInputSerializer(serializers.Serializer):
    operador  = serializers.ChoiceField(
        choices=["=", ">=", "<=", "ENTRE"],
        label="Operador",
        help_text="'=' exato  |  '>=' mínimo  |  '<=' máximo  |  'ENTRE' intervalo",
    )
    valor     = serializers.FloatField(
        required=False,
        label="Valor",
        help_text="Use para operadores '=' '>=', '<='.",
    )
    valor_min = serializers.FloatField(
        required=False,
        label="Valor mínimo",
        help_text="Use para operador 'ENTRE'.",
    )
    valor_max = serializers.FloatField(
        required=False,
        label="Valor máximo",
        help_text="Use para operadores '<=' e 'ENTRE'.",
    )


# ---------------------------------------------------------------------------
# Ingrediente na formulação
# ---------------------------------------------------------------------------

class IngredienteFormulacaoSerializer(serializers.ModelSerializer):
    ingrediente_nome          = serializers.CharField(source="ingrediente.nome",          read_only=True)
    ingrediente_classificacao = serializers.CharField(source="ingrediente.classificacao", read_only=True)
    ingrediente_tipo          = serializers.CharField(source="ingrediente.tipo",          read_only=True)

    class Meta:
        model  = IngredienteFormulacao
        fields = [
            "id", "ingrediente", "ingrediente_nome", "ingrediente_classificacao",
            "ingrediente_tipo", "ms_porcent", "origem_participacao",
            "ms_kg", "mn_kg", "pb_kg", "ndt_kg", "fdn_kg", "ee_kg", "ca_kg", "p_kg",
        ]
        read_only_fields = [
            "id", "ingrediente_nome", "ingrediente_classificacao", "ingrediente_tipo",
            "ms_kg", "mn_kg", "pb_kg", "ndt_kg", "fdn_kg", "ee_kg", "ca_kg", "p_kg",
        ]


class AjustarParticipacaoInputSerializer(serializers.Serializer):
    """
    Front envia percentual (0-100); get_fracao() converte para fração
    (0-1) — único ponto de conversão de escala na camada API.
    """
    ms_porcent = serializers.FloatField(
        min_value=0.0,
        max_value=100.0,
        label="Participação % MS",
        help_text="Percentual de matéria seca (0 a 100).",
    )

    def get_fracao(self) -> float:
        return self.validated_data["ms_porcent"] / 100.0


class AdicionarIngredienteInputSerializer(serializers.Serializer):
    """
    ingrediente_id retorna instância Ingrediente — use .pk no viewset.
    """
    ingrediente_id = serializers.PrimaryKeyRelatedField(
        queryset=Ingrediente.objects.none(),
        label="Ingrediente",
        help_text="Selecione o ingrediente a adicionar.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ingrediente_id"].queryset = _ingredientes_do_usuario(self.context)


# ---------------------------------------------------------------------------
# Sugestões de ingredientes (saída)
# ---------------------------------------------------------------------------

class SugestaoIngredienteSerializer(serializers.Serializer):
    ingrediente_id       = serializers.IntegerField()
    nome                 = serializers.CharField()
    classificacao        = serializers.CharField()
    tipo                 = serializers.CharField()
    custo_kg             = serializers.FloatField()
    # Composição bromatológica
    pb                   = serializers.FloatField()
    ndt                  = serializers.FloatField()
    fdn                  = serializers.FloatField()
    ee                   = serializers.FloatField()
    ca                   = serializers.FloatField()
    p                    = serializers.FloatField()
    # Ranking
    score                = serializers.FloatField()
    distancia_euclidiana = serializers.FloatField(allow_null=True)
    # Projeção what-if (delta % MS se ~5 % for incluído)
    delta_pb             = serializers.FloatField()
    delta_ndt            = serializers.FloatField()
    delta_fdn            = serializers.FloatField()
    delta_ee             = serializers.FloatField()
    delta_ca             = serializers.FloatField()
    delta_p              = serializers.FloatField()


# ---------------------------------------------------------------------------
# Formulação
# ---------------------------------------------------------------------------

class FormulacaoListSerializer(serializers.ModelSerializer):
    lote_nome = serializers.CharField(source="lote.nome_lote", read_only=True)

    class Meta:
        model  = Formulacao
        fields = ["id", "lote", "lote_nome", "titulo", "status", "dt_inc", "dt_alt"]
        read_only_fields = fields


class FormulacaoDetailSerializer(serializers.ModelSerializer):
    lote_nome    = serializers.CharField(source="lote.nome_lote",   read_only=True)
    exigencias   = serializers.SerializerMethodField()
    ingredientes = serializers.SerializerMethodField()

    class Meta:
        model  = Formulacao
        fields = [
            "id", "lote", "lote_nome", "usuario", "titulo", "observacoes",
            "status", "dt_inc", "dt_alt", "exigencias", "ingredientes",
        ]
        read_only_fields = fields

    def get_exigencias(self, obj: Formulacao):
        try:
            exigencia = obj.exigencia_configurada
        except Exception:
            return []
        configs = exigencia.configuracoes_nutrientes.all().order_by("nutriente")
        return ConfiguracaoNutrienteSerializer(configs, many=True).data

    def get_ingredientes(self, obj: Formulacao):
        qs = (
            obj.ingredientes_formulacao
            .select_related("ingrediente")
            .order_by("-ms_porcent")
        )
        return IngredienteFormulacaoSerializer(qs, many=True).data


# ---------------------------------------------------------------------------
# Resultado de adequação (do payload do último snapshot)
# ---------------------------------------------------------------------------

class DesvioOutputSerializer(serializers.Serializer):
    nutriente            = serializers.CharField()
    valor_atual          = serializers.FloatField()
    operador             = serializers.CharField()
    valor_min            = serializers.FloatField(allow_null=True)
    valor_max            = serializers.FloatField(allow_null=True)
    alterado_pelo_usuario = serializers.BooleanField()
    status               = serializers.CharField()
    magnitude_relativa   = serializers.FloatField()


class ResultadoAdequacaoOutputSerializer(serializers.Serializer):
    schema_version     = serializers.IntegerField()
    soma_participacoes = serializers.FloatField()
    soma_valida        = serializers.BooleanField()
    atende_tudo        = serializers.BooleanField()
    desvios            = DesvioOutputSerializer(many=True)


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------

class AlertaSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Alerta
        fields = [
            "id", "nutriente", "tipo", "severidade",
            "valor_atual", "valor_limite", "magnitude_relativa",
            "snapshot_versao_geracao", "snapshot_versao_resolucao",
            "resolvido", "dt_geracao", "dt_resolucao",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Snapshots / versões
# ---------------------------------------------------------------------------

class SnapshotListSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SnapshotFormulacao
        fields = ["id", "versao_num", "motivo", "usuario", "dt_criacao"]
        read_only_fields = fields


class SnapshotDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SnapshotFormulacao
        fields = ["id", "versao_num", "payload", "motivo", "usuario", "dt_criacao"]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Eventos
# ---------------------------------------------------------------------------

class EventoFormulacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = EventoFormulacao
        fields = ["id", "tipo_evento", "payload", "usuario", "dt_criacao"]
        read_only_fields = fields
