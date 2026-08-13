"""Testes das validações aplicadas à manutenção administrativa da tabela NRC."""

from exigencia_nrc.serializers import ExigenciaNRCSerializer


def _linha_nrc(**alteracoes):
    """Monta uma linha pequena e válida para isolar cada regra testada."""
    dados = {
        'categoria': 'cordeiros_4_meses',
        'fase': 'crescimento',
        'pv_kg': 20.0,
        'gmd_kg': 0.2,
    }
    dados.update(alteracoes)
    return dados


def test_exigencia_rejeita_fase_incompativel_com_categoria():
    """Uma linha de cordeiro não pode receber fase exclusiva de ovelhas."""
    serializer = ExigenciaNRCSerializer(data=_linha_nrc(fase='gestacao_tardia'))

    assert not serializer.is_valid()
    assert 'fase' in serializer.errors


def test_exigencia_rejeita_peso_e_gmd_negativos():
    """Valores zootécnicos impossíveis não entram na tabela de referência."""
    serializer = ExigenciaNRCSerializer(data=_linha_nrc(pv_kg=0, gmd_kg=-0.1))

    assert not serializer.is_valid()
    assert 'pv_kg' in serializer.errors
    assert 'gmd_kg' in serializer.errors
