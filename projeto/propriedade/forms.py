from django import forms
import re

from .models import Propriedade

class PropriedadeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PropriedadeForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'
            
        self.fields['nome'].widget.attrs.update({'placeholder': 'Nome da propriedade'}, {'label': 'Nome da propriedade*'}, {'required': 'true'})
        self.fields['cnpj'].widget.attrs.update({'placeholder': ''}, {'label': '00.000.000/0000-00 (opcional)'}, {'required': 'false'}, {'class': 'cnpj-mask'})
        self.fields['proprietario'].widget.attrs.update({'placeholder': 'Nome do proprietário'}, {'label': 'Nome do proprietário*'}, {'required': 'true'})
        self.fields['telefone'].widget.attrs.update({'placeholder': '(00) 00000-0000 (opcional)'}, {'label': 'Telefone (opcional)'}, {'required': 'false'}, {'class': 'phone-mask'} )
        self.fields['uf'].widget.attrs.update({'placeholder': 'UF'}, {'label': 'UF*'}, {'required': 'true'}, {'maxlength': '2'}, {'minlength': '2'}, {'text-transform': 'uppercase'}, {'pattern': '[A-Za-z]{2}'}, {'title': 'Digite a sigla do estado (2 letras)'})
        self.fields['cidade'].widget.attrs.update({'placeholder': 'Cidade'}, {'label': 'Cidade*'}, {'required': 'true'})
        self.fields['localidade'].widget.attrs.update({'placeholder': 'Localidade'}, {'label': 'Localidade*'}, {'required': 'true'}, {'title': 'Digite o bairro, vila ou área rural da propriedade'})
        
    class Meta:
        model = Propriedade
        fields = ['nome', 'cnpj', 'proprietario', 'telefone', 'uf', 'cidade', 'localidade']
            
    def clean_cnpj(self):
        cnpj = self.cleaned_data.get('cnpj')
        if cnpj:
            # Remove caracteres não numéricos
            cnpj = re.sub(r'\D', '', cnpj)
            # Verifica se o CNPJ tem 14 dígitos
            if len(cnpj) != 14:
                raise forms.ValidationError("O CNPJ deve ter 14 dígitos.")
        return cnpj
    
    def clean_uf(self):
        uf = self.cleaned_data.get('uf')
        if uf:
            uf = uf.upper()
            if len(uf) != 2 or not re.match(r'^[A-Z]{2}$', uf):
                raise forms.ValidationError("Digite a sigla do estado (2 letras).")
        return uf
    
    # def clean_telefone(self):
    #     telefone = self.cleaned_data.get('telefone')
    #     if telefone:
    #         # Remove caracteres não numéricos
    #         telefone = re.sub(r'\D', '', telefone)
    #         # Verifica se o telefone tem 15 dígitos ((XX) XXXXX-XXXX)
    #         if len(telefone) != 15:
    #             raise forms.ValidationError("O telefone deve ter 15 dígitos.")
    #     return telefone
    