"""
Serializers DRF para o módulo de formulação.
"""

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Case, IntegerField, Q, Value, When
from rest_framework import serializers

from exigencia_nrc.models import ExigenciaNRC
from formulacao.models import (
    Alerta,
    ConfiguracaoNutriente,
    EventoFormulacao,
    Formulacao,
    IngredienteFormulacao,
    ParametrosViabilidade,
    SnapshotFormulacao,
)
from ingrediente.models import Ingrediente
from lote.models import Lote


# ---------------------------------------------------------------------------
# Helpers de contexto
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
    ordem = Case(
        When(classificacao="volumoso", then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
    )
    if not req:
        return (
            Ingrediente.objects
            .filter(fonte_valadares=True)
            .order_by(ordem, "nome")
        )
    perfil = _perfil(context)
    if perfil is None:
        return (
            Ingrediente.objects
            .filter(fonte_valadares=True)
            .order_by(ordem, "nome")
        )
    return (
        Ingrediente.objects
        .filter(Q(fonte_valadares=True) | Q(usuario=perfil))
        .order_by(ordem, "nome")
    )


# ---------------------------------------------------------------------------
# Exigências NRC
# ---------------------------------------------------------------------------

class ExigenciaNRCSerializer(serializers.ModelSerializer):
    """Representa uma linha NRC completa para seleção na pré-formulação."""
    categoria_display = serializers.CharField(source="get_categoria_display", read_only=True)
    fase_display      = serializers.CharField(source="get_fase_display",      read_only=True)

    class Meta:
        """Expõe todos os valores da linha NRC apenas para leitura."""
        model = ExigenciaNRC
        fields = [
            "id", "categoria", "categoria_display", "fase", "fase_display",
            "pv_kg", "tipo_parto", "pv_nascer_kg", "producao_leite_kg_dia", "gmd_kg", "cms_kg",
            "pb_percentual", "ndt_percentual", "fdn_percentual",
            "ee_percentual", "ca_percentual", "p_percentual", "ca_p_percentual",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Ingredientes disponíveis (listagem)
# ---------------------------------------------------------------------------

class IngredienteDisponivelSerializer(serializers.Serializer):
    """Apresenta um ingrediente selecionável já com o preço pessoal resolvido."""
    id                       = serializers.IntegerField()
    nome                     = serializers.CharField()
    classificacao            = serializers.CharField()
    tipo                     = serializers.CharField()
    ms                       = serializers.FloatField()
    pb                       = serializers.FloatField()
    ndt                      = serializers.FloatField()
    fdn                      = serializers.FloatField()
    ee                       = serializers.FloatField()
    ca                       = serializers.FloatField()
    p                        = serializers.FloatField()
    preco_kg_mn              = serializers.FloatField(source="_preco_usuario", allow_null=True)
    preco_nao_informado      = serializers.SerializerMethodField()
    limite_min_participacao  = serializers.FloatField(allow_null=True)
    limite_max_participacao  = serializers.FloatField(allow_null=True)
    fonte_valadares          = serializers.BooleanField()

    def get_preco_nao_informado(self, obj) -> bool:
        """Distingue preço realmente ausente de um valor numérico válido."""
        return bool(getattr(obj, "_sem_preco", 1))


# ---------------------------------------------------------------------------
# Etapa 1: iniciar formulação
# ---------------------------------------------------------------------------

class IniciarFormulacaoInputSerializer(serializers.Serializer):
    """Valida lote, exigência NRC e identificação da primeira etapa da receita."""
    lote_id = serializers.PrimaryKeyRelatedField(
        queryset=Lote.objects.none(),
        label="Lote",
        help_text="Escolha um dos seus lotes.",
        style={"base_template": "select.html"},
    )
    exigencia_nrc_id = serializers.PrimaryKeyRelatedField(
        queryset=ExigenciaNRC.objects.all().order_by("categoria", "fase", "pv_kg", "gmd_kg"),
        label="Exigência NRC",
        help_text="Tabela NRC de referência para a formulação.",
        style={"base_template": "select.html"},
    )
    titulo = serializers.CharField(
        max_length=200,
        label="Título",
        style={"base_template": "input.html"},
    )
    observacoes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        label="Observações",
        style={"base_template": "textarea.html", "rows": 3},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lote_id"].queryset = _lotes_do_usuario(self.context)


# ---------------------------------------------------------------------------
# Etapa 2: gerar distribuição inicial
# ---------------------------------------------------------------------------

class GerarFormulacaoInicialInputSerializer(serializers.Serializer):
    """Recebe ingredientes e o alvo rígido de volumoso usado na distribuição."""
    percentual_alvo_volumoso = serializers.FloatField(
        required=False,
        min_value=0.0,
        max_value=100.0,
        label="Alvo de volumosos (%)",
        help_text=(
            "Aceita fração (0,50) ou percentual (50). Se omitido, preserva "
            "o alvo já configurado na formulação (50% na primeira geração)."
        ),
        style={"base_template": "input.html"},
    )
    objetivo = serializers.ChoiceField(
        choices=["EQUILIBRADO", "MENOR_CUSTO"],
        required=False,
        default="EQUILIBRADO",
        label="Objetivo da geração",
        help_text=(
            "EQUILIBRADO preserva a distribuição técnica; MENOR_CUSTO usa o "
            "custo cadastrado. Os nutrientes são controlados pelos operadores "
            "configurados na exigência."
        ),
    )
    ingrediente_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Ingrediente.objects.none(),
        required=False,
        label="Ingredientes",
        help_text="Selecione os ingredientes para gerar a formulação inicial.",
        style={"base_template": "select_multiple.html"},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ingrediente_ids"].queryset = _ingredientes_do_usuario(self.context)

    def validate_percentual_alvo_volumoso(self, value: float) -> float:
        """
        Normaliza a entrada para fracao 0-1.

        O front ja enviou esse campo em formatos diferentes ao longo do
        projeto: 0.20 e 20 devem significar o mesmo alvo de 20%.
        """
        valor = float(value)
        return valor / 100.0 if valor > 1.0 else valor


class AtualizarPercentualVolumosoInputSerializer(serializers.Serializer):
    """Valida o novo alvo rígido de volumosos da formulação."""

    percentual_alvo_volumoso = serializers.FloatField(
        min_value=0.0,
        max_value=100.0,
        label="Alvo de volumosos (%)",
        help_text="Aceita fração (0,50) ou percentual (50).",
        style={"base_template": "input.html"},
    )

    def validate_percentual_alvo_volumoso(self, value: float) -> float:
        valor = float(value)
        return valor / 100.0 if valor > 1.0 else valor

# ---------------------------------------------------------------------------
# Exigência configurada
# ---------------------------------------------------------------------------

class ConfiguracaoNutrienteSerializer(serializers.ModelSerializer):
    """Mostra o requisito nutricional normalizado que vale para a formulação."""
    class Meta:
        """Expõe limites normalizados e a origem de cada configuração."""
        model  = ConfiguracaoNutriente
        fields = [
            "id", "nutriente", "operador", "valor_min", "valor_max",
            "valor_origem_nrc", "alterado_pelo_usuario", "dt_alteracao",
        ]
        read_only_fields = fields


class AtualizarExigenciaInputSerializer(serializers.Serializer):
    """Valida os formatos ``=``, ``>=``, ``<=`` e intervalo de um nutriente."""
    operador = serializers.ChoiceField(
        choices=["=", ">=", "<=", "ENTRE"],
        label="Operador",
        help_text="'=' exato  |  '>=' mínimo  |  '<=' máximo  |  'ENTRE' intervalo",
        style={"base_template": "select.html"},
    )
    valor = serializers.FloatField(
        required=False,
        allow_null=True,
        label="Valor",
        help_text="Use para o operadores '='.",
        style={"base_template": "input.html"},
    )
    valor_min = serializers.FloatField(
        required=False,
        allow_null=True,
        label="Valor mínimo",
        help_text="Use para os operadores 'ENTRE' e '>='.",
        style={"base_template": "input.html"},
    )
    valor_max = serializers.FloatField(
        required=False,
        allow_null=True,
        label="Valor máximo",
        help_text="Use para os operadores '<=' e 'ENTRE'.",
        style={"base_template": "input.html"},
    )


# ---------------------------------------------------------------------------
# Ingrediente na formulação
# ---------------------------------------------------------------------------

class IngredienteFormulacaoSerializer(serializers.ModelSerializer):
    """Detalha participação, massas, trava, limite e preço atual da linha."""
    ingrediente_nome          = serializers.CharField(source="ingrediente.nome",          read_only=True)
    ingrediente_classificacao = serializers.CharField(source="ingrediente.classificacao", read_only=True)
    ingrediente_tipo          = serializers.CharField(source="ingrediente.tipo",          read_only=True)
    ingrediente_limite_max_participacao = serializers.FloatField(
        source="ingrediente.limite_max_participacao", read_only=True, allow_null=True,
    )
    ingrediente_limite_min_participacao = serializers.FloatField(
        source="ingrediente.limite_min_participacao", read_only=True, allow_null=True,
    )
    def to_representation(self, instance):
        """Expõe resíduos numéricos sem notação científica enganosa."""
        data = super().to_representation(instance)
        ms_porcent = data.get("ms_porcent")
        if ms_porcent is not None and abs(float(ms_porcent)) < 1e-9:
            data["ms_porcent"] = 0.0
        return data

    class Meta:
        """Entrega campos de entrada, saídas calculadas e metadados de custo."""
        model  = IngredienteFormulacao
        fields = [
            "id", "ingrediente", "ingrediente_nome", "ingrediente_classificacao",
            "ingrediente_tipo", "ingrediente_limite_min_participacao",
            "ingrediente_limite_max_participacao",
            "ms_porcent", "origem_participacao",
            "ms_kg", "mn_kg", "pb_kg", "ndt_kg", "fdn_kg", "ee_kg", "ca_kg", "p_kg",
            "custo_kg_mn_override", "origem_custo", "custo_dia",
        ]
        read_only_fields = [
            "id", "ingrediente_nome", "ingrediente_classificacao", "ingrediente_tipo",
            "ingrediente_limite_min_participacao", "ingrediente_limite_max_participacao",
            "ms_kg", "mn_kg", "pb_kg", "ndt_kg", "fdn_kg", "ee_kg", "ca_kg", "p_kg",
            "custo_kg_mn_override", "origem_custo", "custo_dia",
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
        style={"base_template": "input.html"},
    )

    def get_fracao(self) -> float:
        """Converte o percentual validado da API para a fração 0-1 do domínio."""
        return self.validated_data["ms_porcent"] / 100.0


class AtualizarPrecoInputSerializer(serializers.Serializer):
    """
    Corpo de PATCH /formulacoes/{id}/ingredientes/{ing_form_id}/preco/
    e de PATCH /ingredientes/{id}/preco/.

    escopo só é relevante no endpoint de formulação — o endpoint de
    catálogo (ingrediente/viewsets.py) sempre grava no banco de preços
    regional do usuário (equivalente a escopo='geral'), pois não existe
    conceito de "receita" fora do contexto de uma formulação.
    """
    preco = serializers.FloatField(
        min_value=0.0,
        label="Preço (R$/kg MN)",
        style={"base_template": "input.html"},
    )
    escopo = serializers.ChoiceField(
        choices=[("receita", "Só esta receita"), ("geral", "Banco de preços do usuário")],
        default="geral",
        label="Escopo",
        style={"base_template": "select.html"},
    )


class AdicionarIngredienteInputSerializer(serializers.Serializer):
    """Seleciona um ingrediente visível e uma participação inicial opcional."""
    ingrediente_id = serializers.PrimaryKeyRelatedField(
        queryset=Ingrediente.objects.none(),
        label="Ingrediente",
        help_text="Selecione o ingrediente a adicionar.",
        style={"base_template": "select.html"},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ingrediente_id"].queryset = _ingredientes_do_usuario(self.context)


# ---------------------------------------------------------------------------
# Sugestões de ingredientes (saída)
# ---------------------------------------------------------------------------

class SugestaoIngredienteSerializer(serializers.Serializer):
    """Explica a posição de um candidato no ranking de sugestões."""
    ingrediente_id       = serializers.IntegerField()
    nome                 = serializers.CharField()
    classificacao        = serializers.CharField()
    tipo                 = serializers.CharField()
    custo_kg             = serializers.FloatField()
    pb                   = serializers.FloatField()
    ndt                  = serializers.FloatField()
    fdn                  = serializers.FloatField()
    ee                   = serializers.FloatField()
    ca                   = serializers.FloatField()
    p                    = serializers.FloatField()
    score                = serializers.FloatField()
    distancia_euclidiana = serializers.FloatField(allow_null=True)
    custo_kg_ms             = serializers.FloatField(allow_null=True)
    indice_custo_beneficio  = serializers.FloatField(allow_null=True)
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
    """Entrega os dados compactos usados na listagem de formulações."""
    lote_nome = serializers.CharField(source="lote.nome_lote", read_only=True)

    class Meta:
        """Mantém a listagem compacta e completamente somente leitura."""
        model  = Formulacao
        fields = [
            "id", "lote", "lote_nome", "titulo", "status",
            "percentual_alvo_volumoso", "dt_inc", "dt_alt",
        ]
        read_only_fields = fields


class FormulacaoDetailSerializer(serializers.ModelSerializer):
    """Monta a receita completa com exigências e ingredientes atuais."""
    lote_nome    = serializers.CharField(source="lote.nome_lote",   read_only=True)
    exigencias   = serializers.SerializerMethodField()
    ingredientes = serializers.SerializerMethodField()

    class Meta:
        """Expõe o agregado completo sem aceitar escrita por este serializer."""
        model  = Formulacao
        fields = [
            "id", "lote", "lote_nome", "usuario", "titulo", "observacoes",
            "status", "percentual_alvo_volumoso", "dt_inc", "dt_alt",
            "exigencias", "ingredientes",
        ]
        read_only_fields = fields

    def get_exigencias(self, obj: Formulacao):
        """Retorna requisitos configurados ou lista vazia antes da inicialização."""
        try:
            exigencia = obj.exigencia_configurada
        except ObjectDoesNotExist:
            return []
        configs = exigencia.configuracoes_nutrientes.all().order_by("nutriente")
        return ConfiguracaoNutrienteSerializer(configs, many=True).data

    def get_ingredientes(self, obj: Formulacao):
        """Lista as linhas da receita da maior para a menor participação em MS."""
        qs = (
            obj.ingredientes_formulacao
            .select_related("ingrediente")
            .order_by("-ms_porcent")
        )
        return IngredienteFormulacaoSerializer(qs, many=True).data


# ---------------------------------------------------------------------------
# Resultado de adequação
# ---------------------------------------------------------------------------

class DesvioOutputSerializer(serializers.Serializer):
    """Representa a situação de um nutriente diante do requisito configurado."""
    nutriente             = serializers.CharField()
    valor_atual           = serializers.FloatField()
    operador              = serializers.CharField()
    valor_min             = serializers.FloatField(allow_null=True)
    valor_max             = serializers.FloatField(allow_null=True)
    alterado_pelo_usuario = serializers.BooleanField()
    status                = serializers.CharField()
    magnitude_relativa    = serializers.FloatField()


class CustoIngredienteBreakdownSerializer(serializers.Serializer):
    """Detalha quanto cada ingrediente contribui para o custo diário."""
    ing_form_id  = serializers.IntegerField(source="id")
    ingrediente_nome = serializers.CharField(source="ingrediente.nome")
    ms_porcent   = serializers.FloatField()
    custo_kg_mn  = serializers.FloatField(allow_null=True)
    custo_dia    = serializers.FloatField()
    origem_custo = serializers.CharField()


class CustoFormulacaoOutputSerializer(serializers.Serializer):
    """GET /formulacoes/{id}/custos/ — lê direto dos campos-resumo em Formulacao."""
    custo_mn_kg = serializers.FloatField(allow_null=True)
    custo_ms_kg = serializers.FloatField(allow_null=True)
    custo_animal_dia = serializers.FloatField(allow_null=True)
    custo_lote_dia = serializers.FloatField(allow_null=True)
    tem_ingrediente_sem_preco = serializers.BooleanField()
    breakdown = CustoIngredienteBreakdownSerializer(many=True)


# ---------------------------------------------------------------------------
# Viabilidade — ("Custos e Viabilidade da Dieta")
# ---------------------------------------------------------------------------

class DadosAnimalOutputSerializer(serializers.Serializer):
    """
    Dados do(s) animal(s).
    """
    especie      = serializers.CharField()
    raca         = serializers.CharField(allow_null=True)
    sistema      = serializers.CharField(allow_null=True)
    categoria    = serializers.CharField()
    peso_vivo_kg = serializers.FloatField()


class ParametrosViabilidadeSerializer(serializers.ModelSerializer):
    """
    Índices Zootécnicos + Valor R$/kg PV.

    Usado como saída de leitura (embutido em ViabilidadeOutputSerializer)
    e como saída de escrita (retorno de PATCH .../viabilidade/parametros/).
    """
    class Meta:
        """Protege o vínculo com a formulação e as datas de auditoria."""
        model = ParametrosViabilidade
        fields = [
            "num_animais",
            "gmd_esperado_kg",
            "estimativa_permanencia_dias",
            "peso_entrada_kg",
            "cms_percentual_pv",
            "perdas_alimentos_percentual",
            "preco_venda_kg_pv",
            "dt_alteracao",
        ]
        read_only_fields = ["dt_alteracao"]


class AtualizarParametrosViabilidadeInputSerializer(serializers.Serializer):
    """
    PATCH /formulacoes/{id}/viabilidade/parametros/ — partial update.

    Todos os campos são opcionais (required=False): só os enviados
    entram em validated_data e são repassados ao service, que por sua
    vez só atualiza esses no repositório. Nenhum campo tem default
    aqui de propósito — um default silencioso poderia sobrescrever um
    valor que o usuário não pretendia tocar.
    """
    num_animais = serializers.IntegerField(
        required=False, min_value=1, label="Número de Animais",
        style={"base_template": "input.html"},
    )
    gmd_esperado_kg = serializers.FloatField(
        required=False, min_value=0.0, label="GMD (kg) esperado",
        style={"base_template": "input.html"},
    )
    estimativa_permanencia_dias = serializers.IntegerField(
        required=False, min_value=1, label="Estimativa de permanência (dias)",
        style={"base_template": "input.html"},
    )
    peso_entrada_kg = serializers.FloatField(
        required=False, min_value=0.01, label="Peso Vivo Real (Kg) na Entrada",
        style={"base_template": "input.html"},
    )
    cms_percentual_pv = serializers.FloatField(
        required=False, min_value=0.0001, label="CMS (%) do peso vivo",
        style={"base_template": "input.html"},
    )
    perdas_alimentos_percentual = serializers.FloatField(
        required=False, min_value=0.0, label="Perdas de Alimentos (%)",
        style={"base_template": "input.html"},
    )
    preco_venda_kg_pv = serializers.FloatField(
        required=False, allow_null=True, min_value=0.0,
        label="Preço de venda (R$/kg de PV)",
        style={"base_template": "input.html"},
    )


class IndicesZootecnicosOutputSerializer(serializers.Serializer):
    """Quadro 10 — parte calculada (peso saída, ganho, peso ajustado, CMS kg/dia)."""
    peso_saida_kg    = serializers.FloatField()
    ganho_peso_kg    = serializers.FloatField()
    peso_ajustado_kg = serializers.FloatField()
    cms_kg_dia       = serializers.FloatField()


class LinhaCustoViabilidadeOutputSerializer(serializers.Serializer):
    """Quadro 11 — uma linha (um ingrediente)."""
    ingrediente_id              = serializers.IntegerField(allow_null=True)
    nome                        = serializers.CharField()
    participacao_mn_percentual  = serializers.FloatField()
    consumo_kg_dia_animal       = serializers.FloatField()
    consumo_kg_dia_lote         = serializers.FloatField()
    kg_total_periodo            = serializers.FloatField()
    preco_kg_mn                 = serializers.FloatField()
    investimento_total          = serializers.FloatField()
    percentual_investimento     = serializers.FloatField()
    custo_por_animal            = serializers.FloatField()
    custo_por_animal_dia        = serializers.FloatField()


class ResultadoEconomicoOutputSerializer(serializers.Serializer):
    """Quadro 14 — uma linha (Animal ou Lote)."""
    renda_bruta_total    = serializers.FloatField()
    custo_total          = serializers.FloatField()
    custo_por_dia        = serializers.FloatField()
    viabilidade_total    = serializers.FloatField()
    viabilidade_por_dia  = serializers.FloatField()


class ViabilidadeOutputSerializer(serializers.Serializer):
    """
    GET /formulacoes/{id}/viabilidade/ 

    Nada é persistido além de `parametros` que é input, não resultado.
    """
    dados_animal = DadosAnimalOutputSerializer()
    parametros   = ParametrosViabilidadeSerializer()
    indices      = IndicesZootecnicosOutputSerializer()

    linhas_custo = LinhaCustoViabilidadeOutputSerializer(many=True)
    consumo_total_percentual     = serializers.FloatField()
    consumo_kg_dia_animal_total  = serializers.FloatField()
    consumo_kg_dia_lote_total    = serializers.FloatField()
    kg_total_periodo_total       = serializers.FloatField()
    investimento_total_geral     = serializers.FloatField()
    custo_por_animal_total       = serializers.FloatField()
    custo_por_animal_dia_total   = serializers.FloatField()

    preco_minimo_kg_pv = serializers.FloatField()   # Quadro 12

    resultado_animal = ResultadoEconomicoOutputSerializer()  # Quadro 14
    resultado_lote    = ResultadoEconomicoOutputSerializer()


class ResultadoAdequacaoOutputSerializer(serializers.Serializer):
    """Entrega a soma da dieta e os desvios nutricionais do último recálculo."""
    schema_version     = serializers.IntegerField()
    soma_participacoes = serializers.FloatField()
    soma_valida        = serializers.BooleanField()
    atende_tudo        = serializers.BooleanField()
    desvios            = DesvioOutputSerializer(many=True)


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------

class AlertaSerializer(serializers.ModelSerializer):
    """Expõe alertas ativos com severidade e contexto para a interface."""
    class Meta:
        """Mantém os alertas como saída somente leitura da formulação."""
        model  = Alerta
        fields = [
            "id", "nutriente", "tipo", "severidade",
            "valor_atual", "valor_limite", "magnitude_relativa",
            "ingrediente_formulacao", "ingrediente_nome",
            "snapshot_versao_geracao", "snapshot_versao_resolucao",
            "resolvido", "dt_geracao", "dt_resolucao",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Snapshots / versões
# ---------------------------------------------------------------------------

class SnapshotListSerializer(serializers.ModelSerializer):
    """Lista metadados das versões sem transferir o conteúdo completo."""
    class Meta:
        """Omite o payload pesado e preserva somente os metadados da versão."""
        model  = SnapshotFormulacao
        fields = ["id", "versao_num", "motivo", "usuario", "dt_criacao"]
        read_only_fields = fields


class SnapshotDetailSerializer(serializers.ModelSerializer):
    """Entrega o conteúdo integral de uma versão solicitada explicitamente."""
    class Meta:
        """Inclui o payload completo apenas na consulta de uma versão específica."""
        model  = SnapshotFormulacao
        fields = ["id", "versao_num", "payload", "motivo", "usuario", "dt_criacao"]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Eventos
# ---------------------------------------------------------------------------

class EventoFormulacaoSerializer(serializers.ModelSerializer):
    """Representa um evento imutável da trilha de auditoria da formulação."""
    class Meta:
        """Expõe a trilha de auditoria como registros imutáveis."""
        model  = EventoFormulacao
        fields = ["id", "tipo_evento", "payload", "usuario", "dt_criacao"]
        read_only_fields = fields
