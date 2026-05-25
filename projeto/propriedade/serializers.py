from rest_framework import serializers
from .models import Propriedade

class PropriedadeSerializer(serializers.ModelSerializer):
    # associa o usuário à propriedade criada ou atualizada
    usuario = serializers.HiddenField(default=serializers.CurrentUserDefault())
    
    class Meta:
        #define o modelo e os campos a serem serializados
        model = Propriedade
        fields = ['id', 'usuario', 'nome', 'cnpj', 
                  'proprietario', 'telefone', 'uf', 
                  'cidade', 'localidade', 'dt_cadastro', 
                  'dt_atualizacao',]
        # campos que não podem ser editados pelo user
        read_only_fields = ['id', 'dt_cadastro', 'dt_atualizacao']
        
class PropriedadeListSerializer(serializers.ModelSerializer):
    # usado para listar a propriedade dentro do lote, apenas com as infos mais essenciais para o user saber onde está
    class Meta:
        model = Propriedade
        fields = ['id', 'nome', 'uf', 'cidade']
        