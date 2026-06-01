from django import forms

from .models import (
    FASES_COM_PARTO_E_DIAS,
    FASES_VALIDAS,
    Lote,
)


class LoteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'

        self.fields['nome_lote'].widget.attrs['placeholder'] = 'Ex: Lote Cordeiros Abril'
        self.fields['raca'].widget.attrs['placeholder'] = 'Ex: Santa Inês, Dorper...'
        self.fields['sistema'].widget.attrs['placeholder'] = 'Ex: Confinamento, Semiconfinamento...'
        self.fields['peso_vivo'].widget.attrs['placeholder'] = 'kg'
        self.fields['gmd_esperado'].widget.attrs['placeholder'] = 'kg/dia'
        self.fields['num_animais'].widget.attrs['placeholder'] = 'Ex: 50'
        self.fields['pv_percentual'].widget.attrs['placeholder'] = '% (opcional)'
        self.fields['dias_fase'].widget.attrs['placeholder'] = 'dias'

    class Meta:
        model = Lote
        fields = [
            'nome_lote', 'raca', 'sistema',
            'categoria', 'idade', 'fase',
            'tipo_parto', 'dias_fase',
            'peso_vivo', 'gmd_esperado', 'num_animais', 'pv_percentual',
        ]

    def clean(self):
        cleaned = super().clean()
        categoria = cleaned.get('categoria')
        idade = cleaned.get('idade')
        fase = cleaned.get('fase')
        tipo_parto = cleaned.get('tipo_parto')
        dias_fase = cleaned.get('dias_fase')

        # Valida combinação categoria/idade/fase
        if categoria and idade and fase:
            fases_permitidas = FASES_VALIDAS.get(categoria, {}).get(idade, [])
            if fases_permitidas and fase not in fases_permitidas:
                self.add_error(
                    'fase',
                    f'A fase "{fase}" não é válida para {categoria} na faixa {idade}. '
                    f'Opções: {", ".join(fases_permitidas)}.',
                )

        # tipo_parto e dias_fase obrigatórios para certas fases de ovelha
        if fase in FASES_COM_PARTO_E_DIAS:
            if not tipo_parto:
                self.add_error('tipo_parto', 'Informe o tipo de parto para esta fase.')
            if not dias_fase:
                self.add_error('dias_fase', 'Informe os dias na fase para esta fase.')

        return cleaned