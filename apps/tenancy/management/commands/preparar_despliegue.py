from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Para el Pre-Deploy de Render: migra public y los negocios listos, y registra la plataforma con "
        "sus dominios. Es un solo comando porque Render, en servicios Docker, no pasa el Pre-Deploy por una "
        "shell y no acepta encadenar con &&."
    )

    def handle(self, *args, **options):
        call_command("migrar_esquemas", verbosity=options["verbosity"], stdout=self.stdout)
        call_command("configurar_plataforma", stdout=self.stdout)
