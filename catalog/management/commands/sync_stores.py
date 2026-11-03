from django.core.management.base import BaseCommand, CommandError

from catalog.services import ApiError, sync_stores


class Command(BaseCommand):
    help = "Descarga las tiendas de CheapShark."

    def handle(self, *args, **opts):
        try:
            created = sync_stores()
        except ApiError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"Tiendas sincronizadas ({created} nuevas)."))
