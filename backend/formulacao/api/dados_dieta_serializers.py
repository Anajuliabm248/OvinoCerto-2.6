"""Serializers da fachada somente leitura Dados da Dieta."""

import math

from rest_framework import serializers

from formulacao.api.serializers import DesvioOutputSerializer

# pylint: disable=abstract-method, too-few-public-methods


class DadosDietaQuerySerializer(serializers.Serializer):
    """Valida um override momentâneo da quantidade salva na formulação."""

    quantidade_mistura_mn_kg = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text=(
            "Override opcional da quantidade salva, em kg de MN. "
            "Afeta somente esta consulta e não é persistido."
        ),
    )

    def validate_quantidade_mistura_mn_kg(self, valor):
        """Rejeita zero, negativos e representações não finitas."""
        if valor is None:
            return None
        if not math.isfinite(valor) or valor <= 0:
            raise serializers.ValidationError(
                "Informe um valor finito e maior que zero."
            )
        return valor


class AtualizarQuantidadeMisturaInputSerializer(serializers.Serializer):
    """Valida a quantidade persistida da mistura concentrada em kg de MN."""

    quantidade_mistura_mn_kg = serializers.FloatField(
        required=True,
        allow_null=True,
        help_text=(
            "Quantidade de matéria natural da mistura concentrada a preparar. "
            "Use null para limpar o valor salvo."
        ),
    )

    def validate_quantidade_mistura_mn_kg(self, valor):
        """Aceita vazio ou um valor finito estritamente positivo."""
        if valor is None:
            return None
        if not math.isfinite(valor) or valor <= 0:
            raise serializers.ValidationError(
                "Informe um valor finito e maior que zero."
            )
        return valor


class DadosDietaLinhaSerializer(serializers.Serializer):
    """Linha diária da dieta em matéria seca e matéria natural."""

    ing_form_id = serializers.IntegerField()
    ingrediente_id = serializers.IntegerField(allow_null=True)
    classificacao = serializers.CharField()
    tipo = serializers.CharField()
    nome = serializers.CharField()
    ms_kg_dia = serializers.FloatField()
    mn_kg_dia = serializers.FloatField()
    participacao_ms_percentual = serializers.FloatField()
    participacao_mn_percentual = serializers.FloatField()
    preco_kg_mn = serializers.FloatField(allow_null=True)
    custo_dia = serializers.FloatField()
    origem_custo = serializers.CharField()


class DadosDietaTotaisSerializer(serializers.Serializer):
    """Totais do Quadro 6, incluindo os resumos de custo já existentes."""

    ms_kg_dia = serializers.FloatField()
    mn_kg_dia = serializers.FloatField()
    participacao_ms_percentual = serializers.FloatField()
    participacao_mn_percentual = serializers.FloatField()
    custo_mn_kg = serializers.FloatField(allow_null=True)
    custo_ms_kg = serializers.FloatField(allow_null=True)
    custo_animal_dia = serializers.FloatField(allow_null=True)
    custo_lote_dia = serializers.FloatField(allow_null=True)
    tem_ingrediente_sem_preco = serializers.BooleanField()


class DietaDadosDietaSerializer(serializers.Serializer):
    """Quadro detalhado da dieta."""

    linhas = DadosDietaLinhaSerializer(many=True)
    totais = DadosDietaTotaisSerializer()
    tem_ingrediente_sem_preco = serializers.BooleanField()


class ResumoClassificacaoSerializer(serializers.Serializer):
    """Totais de volumoso, concentrado ou dieta completa."""

    mn_kg_total = serializers.FloatField()
    ms_kg_total = serializers.FloatField()
    participacao_ms_percentual = serializers.FloatField()
    participacao_mn_percentual = serializers.FloatField()


class ResumoPorClassificacaoSerializer(serializers.Serializer):
    """Quadro 6.1 agrupado pela classificação persistida do ingrediente."""

    volumoso = ResumoClassificacaoSerializer()
    concentrado = ResumoClassificacaoSerializer()
    total = ResumoClassificacaoSerializer()


class MisturaConcentradaLinhaSerializer(serializers.Serializer):
    """Proporções de cada concentrado dentro da mistura concentrada."""

    ing_form_id = serializers.IntegerField()
    ingrediente_id = serializers.IntegerField(allow_null=True)
    nome = serializers.CharField()
    participacao_ms_mistura_percentual = serializers.FloatField()
    mn_kg_por_100kg_mistura = serializers.FloatField()
    mn_kg_para_quantidade = serializers.FloatField(allow_null=True)


class MisturaConcentradaTotaisSerializer(serializers.Serializer):
    """Invariantes da mistura; ficam nulos quando ela não está disponível."""

    participacao_ms_mistura_percentual = serializers.FloatField(allow_null=True)
    mn_kg_por_100kg_mistura = serializers.FloatField(allow_null=True)
    mn_kg_para_quantidade = serializers.FloatField(allow_null=True)


class MisturaConcentradaSerializer(serializers.Serializer):
    """Quadro 6.2 normalizado na MN, sem persistir a quantidade simulada."""

    disponivel = serializers.BooleanField()
    motivo_indisponibilidade = serializers.CharField(allow_null=True)
    ms_percentual_mistura = serializers.FloatField(allow_null=True)
    linhas = MisturaConcentradaLinhaSerializer(many=True)
    totais = MisturaConcentradaTotaisSerializer()


class RequisitoDadosDietaSerializer(serializers.Serializer):
    """Requisito completo, sem perder operador nem limites."""

    nutriente = serializers.CharField()
    operador = serializers.CharField()
    valor_min = serializers.FloatField(allow_null=True)
    valor_max = serializers.FloatField(allow_null=True)
    valor_origem_nrc = serializers.FloatField(allow_null=True)
    alterado_pelo_usuario = serializers.BooleanField()


class ComposicaoNutrienteDadosDietaSerializer(serializers.Serializer):
    """Valor da dieta e status correspondente no último snapshot."""

    valor = serializers.FloatField(allow_null=True)
    status = serializers.CharField(allow_null=True)


class ComparacaoNutricionalDadosDietaSerializer(serializers.Serializer):
    """Quadro 7 alimentado pelo último snapshot, não pelas células quebradas."""

    versao_num = serializers.IntegerField()
    ms_concentrado_percentual = serializers.FloatField(allow_null=True)
    requisitos = RequisitoDadosDietaSerializer(many=True)
    composicao_dieta = serializers.DictField(
        child=ComposicaoNutrienteDadosDietaSerializer()
    )
    desvios = DesvioOutputSerializer(many=True)
    custo_mn_kg = serializers.FloatField(allow_null=True)
    custo_animal_dia = serializers.FloatField(allow_null=True)


class AvisoDadosDietaSerializer(serializers.Serializer):
    """Aviso não bloqueante, como preço ausente."""

    codigo = serializers.CharField()
    mensagem = serializers.CharField()
    ing_form_id = serializers.IntegerField(allow_null=True)
    nome = serializers.CharField(allow_null=True)


class DadosDietaOutputSerializer(serializers.Serializer):
    """Contrato agregado do GET /formulacoes/{id}/dados-dieta/."""

    formulacao_id = serializers.IntegerField()
    versao_num = serializers.IntegerField()
    quantidade_mistura_mn_kg = serializers.FloatField(allow_null=True)
    dieta = DietaDadosDietaSerializer()
    resumo_por_classificacao = ResumoPorClassificacaoSerializer()
    mistura_concentrada = MisturaConcentradaSerializer()
    comparacao_nutricional = ComparacaoNutricionalDadosDietaSerializer()
    avisos = AvisoDadosDietaSerializer(many=True)
