from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q

from catalog.models import Game, Store
from catalog.services import ApiError, refresh_games, sync_deals, sync_stores


class Command(BaseCommand):
    help = (
        "Descarga ofertas de CheapShark y guarda precio actual e histórico. "
        "Con --tracked actualiza además todas las tiendas de los juegos con alertas o más visitados."
    )

    def add_arguments(self, parser):
        parser.add_argument("--pages", type=int, default=3, help="Páginas de 60 ofertas a descargar.")
        parser.add_argument("--sort", default="Deal Rating",
                            help="Orden de CheapShark: Deal Rating, Savings, Price, Metacritic, Reviews, Recent…")
        parser.add_argument("--tracked", action="store_true", help="Refrescar juegos con alertas y populares.")
        parser.add_argument("--top", type=int, default=50, help="Cuántos juegos populares refrescar con --tracked.")

    def handle(self, *args, **opts):
        try:
            if not Store.objects.exists():
                sync_stores()
            changed = sync_deals(pages=opts["pages"], sortBy=opts["sort"])
            self.stdout.write(f"Ofertas: {changed} precios nuevos o cambiados.")
            if opts["tracked"]:
                games = list(
                    Game.objects.filter(cheapshark_game_id__isnull=False)
                    .annotate(n_alerts=Count("alerts", filter=Q(alerts__deleted_at__isnull=True)))
                    .order_by("-n_alerts", "-popularity")[: opts["top"]]
                )
                changed = refresh_games(games)
                self.stdout.write(f"Juegos seguidos: {changed} precios nuevos o cambiados.")
        except ApiError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS("Listo."))
