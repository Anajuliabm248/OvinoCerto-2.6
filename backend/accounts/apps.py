""" configurações do app accounts """

from django.apps import AppConfig

class AccountsConfig(AppConfig):
    '''configurações do app accounts'''
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
