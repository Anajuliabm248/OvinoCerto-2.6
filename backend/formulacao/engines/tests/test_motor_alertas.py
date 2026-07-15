"""
pytest formulacao/engines/tests/test_motor_alertas.py -v

Testes de domínio puro (sem banco) do MotorAlertas, focados no novo
alerta de LIMITE_INGREDIENTE (limitação de percentual de inclusão por
ingrediente, ex.: bicarbonato de sódio limitado a 1.5% da MS).
"""

from formulacao.engines.motor_alertas import (
    MotorAlertas,
    ParticipacaoIngredienteLimite,
    ThresholdsSeveridade,
)


def _item(id_=1, nome="Bicarbonato de sódio", fracao=0.0, limite=None):
    return ParticipacaoIngredienteLimite(
        ingrediente_formulacao_id=id_,
        ingrediente_nome=nome,
        fracao_atual=fracao,
        limite_max=limite,
    )


class TestAvaliarLimitesIngredientes:

    def test_sem_limite_configurado_nao_gera_alerta(self):
        itens = [_item(fracao=0.30, limite=None)]
        assert MotorAlertas.avaliar_limites_ingredientes(itens) == []

    def test_dentro_do_limite_nao_gera_alerta(self):
        itens = [_item(fracao=0.014, limite=0.015)]
        assert MotorAlertas.avaliar_limites_ingredientes(itens) == []

    def test_exatamente_no_limite_nao_gera_alerta(self):
        itens = [_item(fracao=0.015, limite=0.015)]
        assert MotorAlertas.avaliar_limites_ingredientes(itens) == []

    def test_excesso_pequeno_gera_info(self):
        # limite 1.5%, atual 1.53% -> magnitude = 0.03/1.5 = 0.02 -> INFO
        itens = [_item(fracao=0.0153, limite=0.015)]
        alertas = MotorAlertas.avaliar_limites_ingredientes(itens)
        assert len(alertas) == 1
        assert alertas[0]["severidade"] == "INFO"

    def test_excesso_moderado_gera_atencao(self):
        # limite 2%, atual 2.2% -> magnitude = 0.2/2 = 0.10 -> ATENCAO
        itens = [_item(fracao=0.022, limite=0.02)]
        alertas = MotorAlertas.avaliar_limites_ingredientes(itens)
        assert alertas[0]["severidade"] == "ATENCAO"

    def test_excesso_grande_gera_critico(self):
        # limite 1.5%, atual 2.5% -> magnitude = 1.0/1.5 = 0.667 -> CRITICO
        itens = [_item(fracao=0.025, limite=0.015)]
        alertas = MotorAlertas.avaliar_limites_ingredientes(itens)
        assert alertas[0]["severidade"] == "CRITICO"

    def test_valores_do_alerta_em_percentual(self):
        itens = [_item(id_=42, nome="Ureia", fracao=0.02, limite=0.015)]
        alertas = MotorAlertas.avaliar_limites_ingredientes(itens)
        alerta = alertas[0]
        assert alerta["tipo"] == "LIMITE_INGREDIENTE"
        assert alerta["nutriente"] is None
        assert alerta["valor_atual"] == 2.0
        assert alerta["valor_limite"] == 1.5
        assert alerta["ingrediente_formulacao_id"] == 42
        assert alerta["ingrediente_nome"] == "Ureia"

    def test_limite_zero_nao_quebra_com_divisao_por_zero(self):
        itens = [_item(fracao=0.01, limite=0.0)]
        alertas = MotorAlertas.avaliar_limites_ingredientes(itens)
        assert len(alertas) == 1
        assert alertas[0]["severidade"] == "CRITICO"
        assert alertas[0]["magnitude_relativa"] == 1.0

    def test_multiplos_ingredientes_geram_um_alerta_cada(self):
        itens = [
            _item(id_=1, nome="Bicarbonato de sódio", fracao=0.025, limite=0.015),
            _item(id_=2, nome="Milho moído", fracao=0.30, limite=None),
            _item(id_=3, nome="Ureia", fracao=0.008, limite=0.01),
        ]
        alertas = MotorAlertas.avaliar_limites_ingredientes(itens)
        # Bicarbonato excede, milho sem limite, ureia dentro do limite
        assert len(alertas) == 1
        assert alertas[0]["ingrediente_formulacao_id"] == 1

    def test_thresholds_customizados_sao_respeitados(self):
        thresholds = ThresholdsSeveridade(info_max=0.5, atencao_max=0.9)
        itens = [_item(fracao=0.022, limite=0.02)]  # magnitude 0.10
        alertas = MotorAlertas.avaliar_limites_ingredientes(itens, thresholds)
        assert alertas[0]["severidade"] == "INFO"

    def test_lista_vazia_retorna_lista_vazia(self):
        assert MotorAlertas.avaliar_limites_ingredientes([]) == []
