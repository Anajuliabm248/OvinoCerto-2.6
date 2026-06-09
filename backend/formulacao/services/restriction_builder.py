"""
Constrói restrições nutricionais a partir da exigência NRC.

Todos os valores trabalham em % base MS, igual aos campos
do model Ingrediente (pb, ndt, fdn, ee, ca, p).

Operadores:
  PB  >= mínimo  (animais precisam de pelo menos X% de proteína)
  NDT >= mínimo  (energia digestível mínima)
  FDN <= máximo  (fibra não pode ser excessiva)
  EE  >= mínimo  (extrato etéreo mínimo)
  Ca  >= mínimo  (cálcio mínimo — NÃO usar '=' pois causa infeasibility)
  P   >= mínimo  (fósforo mínimo)
"""


class RestrictionBuilder:

    # Mapeamento: (campo na ExigenciaNRC, chave do nutriente, operador)
    _MAPA = [
        ('pb_percentual',  'PB',  '>='),
        ('ndt_percentual', 'NDT', '>='),
        ('fdn_percentual', 'FDN', '<='),
        ('ee_percentual',  'EE',  '>='),
        ('ca_percentual',  'Ca',  '>='),
        ('p_percentual',   'P',   '>='),
    ]

    @staticmethod
    def build_restricoes(exigencia_nrc):
        """
        Retorna lista de restrições nutricionais prontas para o solver.

        Args:
            exigencia_nrc: objeto ExigenciaNRC

        Returns:
            list[{nutriente, operador, valor}]
        """
        restricoes = []
        for attr, nutriente, operador in RestrictionBuilder._MAPA:
            valor = getattr(exigencia_nrc, attr, None)
            if valor is None or valor <= 0:
                continue
            restricoes.append({
                'nutriente': nutriente,
                'operador':  operador,
                'valor':     float(valor),
            })
        return restricoes

    @staticmethod
    def validar_restricoes(restricoes):
        if not restricoes:
            return False, "Nenhuma restrição nutricional gerada a partir da exigência NRC"
        return True, ""
