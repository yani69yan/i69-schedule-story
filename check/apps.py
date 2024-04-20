from django.apps import AppConfig
from django.core.management import call_command
import os


class CheckConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "check"

    def ready(self):
        call_command("check_connections")
