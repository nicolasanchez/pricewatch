from django.core.management.base import BaseCommand, CommandError

from catalog.services import ApiError, sync_rates


class Command(BaseCommand):
    help = "Descarga los tipos de cambio del día (Banco Central Europeo, vía Frankfurter)."

    def handle(self, *args, **opts):
        try:
            saved, day = sync_rates()
        except ApiError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"{saved} tipos de cambio guardados para el {day:%d/%m/%Y}."))
