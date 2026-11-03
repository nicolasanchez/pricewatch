from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Tarea programada: tipos de cambio + ofertas + comprobación de alertas, en ese orden."

    def handle(self, *args, **opts):
        for name, kwargs in [("sync_rates", {}), ("sync_deals", {"tracked": True}), ("check_alerts", {})]:
            self.stdout.write(f"→ {name}")
            try:
                call_command(name, **kwargs)
            except Exception as exc:  # una API caída no debe impedir el resto
                self.stderr.write(self.style.WARNING(f"{name} falló: {exc}"))
