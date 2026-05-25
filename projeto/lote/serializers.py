from rest_framework import serializers
from .models import Lote, FASES_VALIDAS, FAZES_COM_PARTO_E_DIAS

class LoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lote
        fields = ['id', 'propriedade', 'nome_lote', 'raca', 'sistema', 'categoria', 'idade', 'fase', 
                  'tipo_parto', 'dias_fase', 'peso_vivo', 'gmd_esperado', 'num_animais', 'pv_percentual', 'dt_cadastro', 'dt_atualizacao']
        read_only_fields = ['id', 'dt_cadastro', 'dt_atualizacao', 'pv_percentual']
        
    def validate(self, data):
        categoria = data.get('categoria') or getattr(self.instance, 'categoria', None)
        idade = data.get('idade') or getattr(self.instance, 'idade', None)
        fase = data.get('fase') or getattr(self.instance, 'fase', None)
        tipo_parto = data.get('tipo_parto')
        dias_fase = data.get('dias_fase')
        
        fases_validas = FASES_VALIDAS.get(categoria, {}).get(idade, [])
        if fase and fase not in fases_validas:
            raise serializers.ValidationError(
                f"Fase '{fase}' não é válida para categoria '{categoria}' e idade '{idade}'."
                f"Fases válidas: {", ".join(fases_validas)}.")
            
        if categoria == 'ovelha' and fase in FAZES_COM_PARTO_E_DIAS:
            if tipo_parto is None:
                raise serializers.ValidationError(
                    f"Fase '{fase}' exige que informe o tipo de parto.")
            if dias_fase is None:
                raise serializers.ValidationError(
                    f"Fase '{fase}' exige que informe os dias na fase atual.")
        
        else:
            #se não for fase de gestação ou lactação, tipo_parto e dias_fase devem ser nulos
            data['tipo_parto'] = None
            data['dias_fase'] = None
            
        return data
    
    def validate_num_animais(self, value):
        if value <= 0:
            raise serializers.ValidationError("O número de animais deve ser maior que zero.")
        return value
    
    def validate_peso_vivo(self, value):
        if value <= 0:
            raise serializers.ValidationError("O peso vivo deve ser maior que zero.")
        return value
    
    def validate_gmd_esperado(self, value):
        if value <= 0:
            raise serializers.ValidationError("O ganho médio diário esperado deve ser maior que zero.")
        return value
    
    def validate_pv_percentual(self, value):
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("O percentual do peso vivo deve estar entre 0 e 100.")
        return value
    
    def validate_propriedade(self, propriedade):
        request = self.context['request']
        user = request.user
        if not user.admin and propriedade.usuario != user:
            raise serializers.ValidationError("Você não tem permissão para associar este lote a esta propriedade.")
        return propriedade