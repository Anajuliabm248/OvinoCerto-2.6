from django import forms
import re

from .models import Propriedade

class PropriedadeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        field_options = {
            'nome': {
                'label': 'Nome da propriedade',
                'required': True,
                'attrs': {'placeholder': 'Nome da propriedade'},
            },
            'cnpj': {
                'label': 'CNPJ (opcional)',
                'required': False,
                'attrs': {
                    'placeholder': '00.000.000/0000-00',
                    'class': 'cnpj-mask',
                },
            },
            'proprietario': {
                'label': 'Nome do proprietário',
                'required': True,
                'attrs': {'placeholder': 'Nome do proprietário'},
            },
            'telefone': {
                'label': 'Telefone (opcional)',
                'required': False,
                'attrs': {
                    'placeholder': '(00) 00000-0000',
                    'class': 'phone-mask',
                },
            },
            'uf': {
                'label': 'UF',
                'required': True,
                'attrs': {
                    'placeholder': 'UF',
                    'maxlength': '2',
                    'minlength': '2',
                    'style': 'text-transform: uppercase;',
                    'pattern': '[A-Za-z]{2}',
                    'title': 'Digite a sigla do estado (2 letras)',
                },
            },
            'cidade': {
                'label': 'Cidade',
                'required': True,
                'attrs': {'placeholder': 'Cidade'},
            },
            'localidade': {
                'label': 'Localidade',
                'required': True,
                'attrs': {
                    'placeholder': 'Localidade',
                    'title': 'Digite o bairro, vila ou área rural da propriedade',
                },
            },
        }

        for name, field in self.fields.items():
            options = field_options[name]
            field.label = options['label']
            field.required = options['required']

            attrs = {'class': 'form-control'}
            extra_attrs = options['attrs'].copy()
            extra_class = extra_attrs.pop('class', None)
            if extra_class:
                attrs['class'] = f"{attrs['class']} {extra_class}"
            attrs.update(extra_attrs)
            field.widget.attrs.update(attrs)
        
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
    
