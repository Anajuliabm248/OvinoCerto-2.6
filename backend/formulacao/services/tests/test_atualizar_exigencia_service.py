import pytest

from formulacao.domain.requisito import Operador
from formulacao.services.atualizar_exigencia_service import AtualizarExigenciaService


@pytest.mark.parametrize(
    ("operador", "valor", "valor_min", "valor_max", "esperado"),
    [
        (Operador.IGUAL, 15.0, None, None, (15.0, 15.0)),
        (Operador.MAIOR_IGUAL, 14.0, None, None, (14.0, None)),
        (Operador.MENOR_IGUAL, 4.0, None, None, (None, 4.0)),
        (Operador.ENTRE, None, 14.0, 18.0, (14.0, 18.0)),
    ],
)
def test_normaliza_operadores_conforme_contrato_da_api(
    operador,
    valor,
    valor_min,
    valor_max,
    esperado,
):
    assert AtualizarExigenciaService._normalizar_limites(
        operador,
        valor,
        valor_min,
        valor_max,
    ) == esperado


def test_maior_igual_tambem_aceita_formato_normalizado_legado():
    assert AtualizarExigenciaService._normalizar_limites(
        Operador.MAIOR_IGUAL,
        None,
        14.0,
        None,
    ) == (14.0, None)
