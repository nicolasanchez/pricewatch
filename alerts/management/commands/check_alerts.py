from django.core.management.base import BaseCommand

from alerts.services import check_all_alerts, send_digests


class Command(BaseCommand):
    help = "Comprueba las alertas activas, crea avisos y envía correos. Con --digest envía los resúmenes."

    def add_arguments(self, parser):
        parser.add_argument("--digest", choices=["daily", "weekly"], help="Enviar el resumen del periodo.")

    def handle(self, *args, **opts):
        if opts["digest"]:
            sent = send_digests(opts["digest"])
            self.stdout.write(self.style.SUCCESS(f"{sent} resúmenes enviados."))
            return
        notifications = check_all_alerts()
        self.stdout.write(self.style.SUCCESS(f"{len(notifications)} avisos nuevos."))
