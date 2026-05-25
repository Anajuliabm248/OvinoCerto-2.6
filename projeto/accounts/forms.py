from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import Perfil, Usuario


User = get_user_model()

# Mixin para aplicar classes CSS e evitar repetição de código nos formulários de usuário
class FormControlMixin:
    def aplicar_classes(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            else:
                widget.attrs.setdefault('class', 'form-control')

# Formulário base para cadastro e edição de usuários, com validações comuns
class DadosUsuarioMixin(FormControlMixin, forms.Form):
    nome = forms.CharField(label='Nome', max_length=100, required=True)
    email = forms.EmailField(label='E-mail', required=True)  # Será usado como username também
    cpf = forms.CharField(label='CPF ou CNPJ', max_length=14, required=True)
    telefone = forms.CharField(label='Telefone', max_length=15, required=True)
    estado = forms.CharField(label='Estado', max_length=50, required=True)
    cidade = forms.CharField(label='Cidade', max_length=50, required=True)
    profissao = forms.CharField(label='Profissao', max_length=100, required=True)
    produtor_ovinos = forms.BooleanField(
        label='Produtor de ovinos',
        required=False,
    )

    def __init__(self, *args, user_instance=None, perfil_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_instance = user_instance
        self.perfil_instance = perfil_instance
        self.aplicar_classes()

        if user_instance and not self.is_bound: #is_bound indica se o formulário foi submetido com dados (True) ou se está sendo exibido pela primeira vez (False)
            self.fields['nome'].initial = (
                getattr(perfil_instance, 'nome', '')
                or user_instance.get_full_name()
                or user_instance.username
            )
            self.fields['email'].initial = getattr(perfil_instance, 'email', '') or user_instance.email
            if perfil_instance:
                for field_name in ('cpf', 'telefone', 'estado', 'cidade', 'profissao', 'produtor_ovinos'):
                    self.fields[field_name].initial = getattr(perfil_instance, field_name)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()

        if len(email) > User._meta.get_field('username').max_length:
            raise ValidationError('Use um e-mail com ate 150 caracteres.')

        users = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email))
        if self.user_instance:
            users = users.exclude(pk=self.user_instance.pk)
        if users.exists():
            raise ValidationError('Ja existe um usuario com este e-mail.')

        perfis = Usuario.objects.filter(email__iexact=email)
        if self.perfil_instance:
            perfis = perfis.exclude(pk=self.perfil_instance.pk)
        if perfis.exists():
            raise ValidationError('Ja existe um perfil com este e-mail.')

        return email

    def clean_cpf(self):
        cpf = self.cleaned_data['cpf'].strip()
        perfis = Usuario.objects.filter(cpf=cpf)
        if self.perfil_instance:
            perfis = perfis.exclude(pk=self.perfil_instance.pk)
        if perfis.exists():
            raise ValidationError('Ja existe um usuario com este CPF ou CNPJ.')
        return cpf

    def salvar_user(self, user=None, password=None):
        email = self.cleaned_data['email']
        nome = self.cleaned_data['nome']

        if user is None:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=nome,
            )
        else:
            user.username = email
            user.email = email
            user.first_name = nome
            if password:
                user.set_password(password)
            user.save()

        return user

    def salvar_perfil(self, user, perfil=Perfil.USER):
        dados = {
            'nome': self.cleaned_data['nome'],
            'email': self.cleaned_data['email'],
            'cpf': self.cleaned_data['cpf'],
            'telefone': self.cleaned_data['telefone'],
            'estado': self.cleaned_data['estado'],
            'cidade': self.cleaned_data['cidade'],
            'profissao': self.cleaned_data['profissao'],
            'produtor_ovinos': self.cleaned_data['produtor_ovinos'],
            'perfil': perfil,
        }

        perfil_usuario, _ = Usuario.objects.update_or_create(
            user=user,
            defaults=dados,
        )
        return perfil_usuario


class CadastroUsuarioForm(DadosUsuarioMixin):
    senha1 = forms.CharField(
        label='Senha',
        strip=False,
        widget=forms.PasswordInput,
        help_text=password_validation.password_validators_help_text_html(),
    )
    senha2 = forms.CharField(
        label='Confirmar senha',
        strip=False,
        widget=forms.PasswordInput,
    )

    def clean_senha2(self):
        senha1 = self.cleaned_data.get('senha1')
        senha2 = self.cleaned_data.get('senha2')
        if senha1 and senha2 and senha1 != senha2:
            raise ValidationError('As senhas nao conferem.')
        if senha1:
            validate_password(senha1)
        return senha2

    def save(self):
        user = self.salvar_user(password=self.cleaned_data['senha1'])
        self.salvar_perfil(user)
        return user


class LoginUsuarioForm(FormControlMixin, forms.Form):
    email = forms.EmailField(label='E-mail')
    senha = forms.CharField(
        label='Senha',
        strip=False,
        widget=forms.PasswordInput,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.aplicar_classes()

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email', '').strip().lower()
        senha = cleaned_data.get('senha')

        if email and senha:
            user_obj = User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).first()
            username = user_obj.username if user_obj else email
            self.user = authenticate(username=username, password=senha)

            if self.user is None:
                raise ValidationError('E-mail ou senha invalidos.')
            if not self.user.is_active:
                raise ValidationError('Esta conta esta inativa.')

        return cleaned_data


class PerfilUsuarioForm(DadosUsuarioMixin):
    def save(self):
        user = self.salvar_user(user=self.user_instance)
        perfil_atual = self.perfil_instance.perfil if self.perfil_instance else Perfil.USER
        self.salvar_perfil(user, perfil=perfil_atual)
        return user


class AdminUsuarioForm(DadosUsuarioMixin):
    perfil = forms.ChoiceField(label='Perfil', choices=Perfil.choices)
    is_active = forms.BooleanField(label='Usuario ativo', required=False)
    is_staff = forms.BooleanField(label='Acesso ao Django admin', required=False)
    senha1 = forms.CharField(
        label='Senha',
        strip=False,
        widget=forms.PasswordInput,
        required=False,
        help_text='Obrigatoria ao criar um usuario.',
    )
    senha2 = forms.CharField(
        label='Confirmar senha',
        strip=False,
        widget=forms.PasswordInput,
        required=False,
    )

    def __init__(self, *args, actor=None, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        self.fields['perfil'].initial = getattr(self.perfil_instance, 'perfil', Perfil.USER)
        self.fields['is_active'].initial = True if self.user_instance is None else self.user_instance.is_active
        self.fields['is_staff'].initial = False if self.user_instance is None else self.user_instance.is_staff
        if self.user_instance is None:
            self.fields['senha1'].required = True
            self.fields['senha2'].required = True
        if not (actor and actor.is_superuser):
            self.fields.pop('is_staff')
        self.aplicar_classes()

    def clean_senha2(self):
        senha1 = self.cleaned_data.get('senha1')
        senha2 = self.cleaned_data.get('senha2')

        if self.user_instance is None and not senha1:
            raise ValidationError('Informe uma senha para o novo usuario.')
        if senha1 or senha2:
            if senha1 != senha2:
                raise ValidationError('As senhas nao conferem.')
            validate_password(senha1, self.user_instance)

        return senha2

    def save(self):
        user = self.salvar_user(
            user=self.user_instance,
            password=self.cleaned_data.get('senha1') or None,
        )
        user.is_active = self.cleaned_data.get('is_active', False)
        if 'is_staff' in self.fields:
            user.is_staff = self.cleaned_data.get('is_staff', False)
        user.save()
        self.salvar_perfil(user, perfil=self.cleaned_data['perfil'])
        return user
