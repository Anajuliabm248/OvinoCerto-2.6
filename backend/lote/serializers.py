"""Validação e representação dos dados zootécnicos de um lote."""

from rest_framework import serializers
from propriedade.models import Propriedade

from .models import FASES_COM_PARTO_E_DIAS, FASES_VALIDAS, FASE_CHOICES, Lote

# pylint: disable= no-member, too-few-public-methods

FASE_LABELS = dict(FASE_CHOICES)

class LoteSerializer(serializers.ModelSerializer):
    """Expõe lotes e impede combinações zootécnicas incoerentes."""
    propriedade_nome = serializers.CharField(source='propriedade.nome', read_only=True)

    def __init__(self, *args, **kwargs):
        """Limita o seletor de propriedades às que o usuário pode utilizar."""
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not request or request.user.is_staff or request.user.is_superuser:
            return

        perfil = getattr(request.user, 'perfil_usuario', None)
        if perfil is None:
            self.fields['propriedade'].queryset = Propriedade.objects.none()
        else:
            self.fields['propriedade'].queryset = Propriedade.objects.filter(usuario=perfil)

    class Meta:
        """Declara os campos públicos e protege os campos de auditoria."""
        model = Lote
        fields = [
            'id',
            'propriedade',
            'propriedade_nome',
            'nome_lote',
            'raca',
            'sistema',
            'categoria',
            'fase',
            'tipo_parto',
            'pv_nascer_kg',
            'producao_leite_kg_dia',
            'peso_vivo',
            'gmd_esperado',
            'num_animais',
            'pv_percentual',
            'dt_cadastro',
            'dt_atualizacao',
        ]
        read_only_fields = ['id', 'dt_cadastro', 'dt_atualizacao']

    def validate(self, attrs):
        """Confere fase, categoria e os valores usados nos cálculos nutricionais."""
        instance = getattr(self, 'instance', None)
        categoria = attrs.get('categoria', getattr(instance, 'categoria', None))
        fase = attrs.get('fase', getattr(instance, 'fase', None))
        tipo_parto = attrs.get('tipo_parto', getattr(instance, 'tipo_parto', None))

        if categoria and fase:
            fases_permitidas = FASES_VALIDAS.get(categoria, [])
            if fases_permitidas and fase not in fases_permitidas:
                opcoes = ', '.join(FASE_LABELS.get(valor, valor) for valor in fases_permitidas)
                raise serializers.ValidationError({
                    'fase': (
                        f'A fase "{FASE_LABELS.get(fase, fase)}" não é válida para esta categoria. '
                        f'Opções: {opcoes}.'
                    )
                })

        if fase in FASES_COM_PARTO_E_DIAS:
            errors = {}
            if categoria != 'ovelhas':
                errors['fase'] = 'Fases de gestação e lactação são válidas apenas para ovelhas.'
            if not tipo_parto:
                errors['tipo_parto'] = 'Informe o tipo de parto para esta fase.'
            if errors:
                raise serializers.ValidationError(errors)
        else:
            attrs['tipo_parto'] = None

        erros_numericos = {}
        peso_vivo = attrs.get('peso_vivo', getattr(instance, 'peso_vivo', None))
        gmd = attrs.get('gmd_esperado', getattr(instance, 'gmd_esperado', None))
        num_animais = attrs.get('num_animais', getattr(instance, 'num_animais', None))
        pv_percentual = attrs.get('pv_percentual', getattr(instance, 'pv_percentual', None))
        pv_nascer = attrs.get('pv_nascer_kg', getattr(instance, 'pv_nascer_kg', None))
        producao_leite = attrs.get(
            'producao_leite_kg_dia',
            getattr(instance, 'producao_leite_kg_dia', None),
        )

        if peso_vivo is not None and peso_vivo <= 0:
            erros_numericos['peso_vivo'] = 'Informe um peso vivo maior que zero.'
        if gmd is not None and gmd < 0:
            erros_numericos['gmd_esperado'] = 'O ganho médio diário não pode ser negativo.'
        if num_animais is not None and num_animais <= 0:
            erros_numericos['num_animais'] = 'O lote precisa ter pelo menos um animal.'
        if pv_percentual is not None and not 0 < pv_percentual <= 100:
            erros_numericos['pv_percentual'] = 'O percentual do peso vivo deve estar entre 0 e 100%.'
        if pv_nascer is not None and pv_nascer <= 0:
            erros_numericos['pv_nascer_kg'] = 'O peso ao nascer deve ser maior que zero.'
        if producao_leite is not None and producao_leite < 0:
            erros_numericos['producao_leite_kg_dia'] = 'A produção de leite não pode ser negativa.'
        if erros_numericos:
            raise serializers.ValidationError(erros_numericos)

        return attrs
