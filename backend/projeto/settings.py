"""Configuração central do backend.

Os valores que mudam entre desenvolvimento e produção vêm de variáveis de
ambiente. Em desenvolvimento o projeto continua funcionando sem arquivo
``.env``; em produção, segredo, hosts e banco devem ser informados de forma
explícita para evitar uma inicialização insegura por acidente.
"""

import os
from pathlib import Path
from datetime import timedelta
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / '.env')

def _env_bool(nome: str, padrao: bool = False) -> bool:
    """Lê uma variável booleana aceitando os formatos comuns de ``.env``."""
    valor = os.environ.get(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in {'1', 'true', 'sim', 'yes', 'on'}


def _env_lista(nome: str, padrao: list[str]) -> list[str]:
    """Converte uma variável separada por vírgulas em uma lista limpa."""
    valor = os.environ.get(nome)
    if not valor:
        return padrao
    return [item.strip() for item in valor.split(',') if item.strip()]


DEBUG = _env_bool('DEBUG', True)

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('Defina DJANGO_SECRET_KEY quando DEBUG estiver desativado.')
    SECRET_KEY = 'django-insecure-apenas-para-desenvolvimento-local'

ALLOWED_HOSTS = _env_lista('ALLOWED_HOSTS', ['localhost', '127.0.0.1'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Terceiros
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    # Apps do projeto
    'accounts.apps.AccountsConfig',
    'propriedade.apps.PropriedadeConfig',
    'lote.apps.LoteConfig',
    'exigencia_nrc.apps.ExigenciaNrcConfig',
    'ingrediente.apps.IngredienteConfig',
    'formulacao.apps.FormulacaoConfig',
    # drf-spectacular
    'drf_spectacular',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'projeto.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'projeto.wsgi.application'


# Banco de dados
_use_sqlite = _env_bool('USE_SQLITE', True)

if _use_sqlite:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME':     os.environ.get('DB_NAME',     'ovino_certo'),
            'USER':     os.environ.get('DB_USER',     'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST':     os.environ.get('DB_HOST',     'localhost'),
            'PORT':     os.environ.get('DB_PORT',     '5432'),
            'OPTIONS':  {'connect_timeout': 10},
        }
    }

# Validação de senha
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internacionalização
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True


# Arquivos estáticos / media
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# CORS
CORS_ALLOWED_ORIGINS = _env_lista('CORS_ALLOWED_ORIGINS', [
    'http://localhost:3000',
    'http://localhost:5173',
])
CORS_ALLOW_CREDENTIALS = True


# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # Mantido para o Django Admin e api-auth/ browser
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # drf-spectacular
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.BrowsableAPIRenderer",
        "rest_framework.renderers.JSONRenderer",
    ],
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'API OvinoCerto',
    'DESCRIPTION': 'projeto de formulação automatizado de ração para ovinos da UFSM',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# JWT (Simple JWT)
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}
