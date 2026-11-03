"""Datos de ejemplo para enseñar la web sin depender de la API.

Crea tiendas, 13 juegos con precios en varias tiendas, histórico y tipos de cambio.
Con --user crea además una cuenta de demostración con alertas y avisos.
Los precios se escriben en euros (como en el boceto) y se guardan en dólares,
que es como los devuelve CheapShark.
"""
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.currency import clear_rates_cache
from catalog.models import Deal, ExchangeRate, Game, PriceSnapshot, Store

DEMO_RATES = {"USD": "1.08", "GBP": "0.84", "CHF": "0.94", "SEK": "11.50",
              "PLN": "4.30", "MXN": "21.50", "BRL": "6.10"}
USD_PER_EUR = Decimal(DEMO_RATES["USD"])

STORES = [
    # cheapshark_id, nombre, web, oficial
    (1, "Steam", "https://store.steampowered.com", True),
    (3, "Green Man Gaming", "https://www.greenmangaming.com", True),
    (7, "GOG", "https://www.gog.com", True),
    (11, "Humble Store", "https://www.humblebundle.com/store", True),
    (15, "Fanatical", "https://www.fanatical.com", True),
    (25, "Epic Games Store", "https://store.epicgames.com", True),
    (9001, "Instant Gaming", "https://www.instant-gaming.com", False),
]

# título, steam_app_id, desarrollador, género, metacritic, % Steam, precio base €, {tienda: precio €}
GAMES = [
    ("Hades II", 1145350, "Supergiant Games", "Roguelike", 95, 96, "29.99",
     {"Steam": "23.99", "Instant Gaming": "24.05", "Green Man Gaming": "24.29", "Fanatical": "24.49",
      "Humble Store": "26.99", "Epic Games Store": "29.99"}),
    ("Baldur's Gate 3", 1086940, "Larian Studios", "RPG", 96, 96, "59.99",
     {"GOG": "44.99", "Steam": "47.99", "Instant Gaming": "41.20", "Green Man Gaming": "46.79"}),
    ("Cyberpunk 2077", 1091500, "CD Projekt Red", "RPG", 86, 82, "59.99",
     {"GOG": "29.99", "Steam": "29.99", "Epic Games Store": "29.99", "Instant Gaming": "27.50"}),
    ("Stardew Valley", 413150, "ConcernedApe", "Simulación", 89, 98, "13.99",
     {"Steam": "11.99", "GOG": "11.99", "Humble Store": "12.59"}),
    ("Hollow Knight", 367520, "Team Cherry", "Metroidvania", 87, 97, "14.99",
     {"Humble Store": "7.49", "Steam": "7.49", "GOG": "7.49", "Fanatical": "7.99"}),
    ("Elden Ring", 1245620, "FromSoftware", "Acción", 94, 92, "59.99",
     {"Instant Gaming": "37.19", "Steam": "41.99", "Green Man Gaming": "40.79", "Fanatical": "39.59"}),
    ("Balatro", 2379780, "LocalThunk", "Cartas", 90, 97, "14.99",
     {"Steam": "12.74", "Humble Store": "12.74", "Green Man Gaming": "12.99"}),
    ("Red Dead Redemption 2", 1174180, "Rockstar Games", "Mundo abierto", 93, 90, "59.99",
     {"Fanatical": "19.79", "Steam": "19.79", "Epic Games Store": "19.79", "Green Man Gaming": "20.39"}),
    ("Celeste", 504230, "Maddy Makes Games", "Plataformas", 92, 97, "19.99",
     {"GOG": "4.99", "Steam": "4.99", "Humble Store": "5.49"}),
    ("Terraria", 105600, "Re-Logic", "Sandbox", 83, 97, "9.99",
     {"Steam": "4.99", "GOG": "4.99"}),
    ("Dead Cells", 588650, "Motion Twin", "Roguelike", 89, 94, "24.99",
     {"Green Man Gaming": "9.99", "Steam": "9.99", "GOG": "9.99"}),
    ("Slay the Spire", 646570, "Mega Crit", "Cartas", 89, 97, "24.99",
     {"Fanatical": "5.99", "Steam": "6.24", "GOG": "6.24"}),
    ("Hades", 1145360, "Supergiant Games", "Roguelike", 93, 98, "24.99",
     {"Steam": "6.24", "Epic Games Store": "6.24", "Humble Store": "6.99"}),
]

# Histórico del ejemplo del boceto (Hades II): fecha relativa en días, precio €, tienda.
HADES_HISTORY = [
    (354, "29.99", "Steam"), (310, "23.99", "Steam"), (292, "29.99", "Steam"),
    (256, "26.99", "Green Man Gaming"), (229, "29.99", "Steam"), (192, "22.49", "Fanatical"),
    (130, "19.99", "Steam"), (106, "29.99", "Steam"), (70, "25.49", "Humble Store"),
    (34, "29.99", "Steam"), (18, "23.99", "Steam"),
]


def usd(eur):
    return (Decimal(eur) * USD_PER_EUR).quantize(Decimal("0.01"), ROUND_HALF_UP)


class Command(BaseCommand):
    help = "Carga datos de ejemplo (tiendas, juegos, histórico, tipos de cambio)."

    def add_arguments(self, parser):
        parser.add_argument("--user", help="Correo de una cuenta demo con alertas.")
        parser.add_argument("--password", default="pricewatch-demo", help="Contraseña de la cuenta demo.")

    @transaction.atomic
    def handle(self, *args, **opts):
        now = timezone.now()
        if not ExchangeRate.objects.exists():
            for code, rate in DEMO_RATES.items():
                ExchangeRate.objects.create(currency=code, rate=Decimal(rate), date=(now - timedelta(days=1)).date())
            clear_rates_cache()

        stores = {}
        for cid, name, web, official in STORES:
            store, _ = Store.objects.update_or_create(
                cheapshark_id=cid, defaults={"name": name, "website": web, "is_official": official, "is_active": True}
            )
            stores[name] = store

        for rank, (title, app_id, dev, genre, mc, st, base, prices) in enumerate(GAMES, start=1):
            game, _ = Game.objects.update_or_create(
                title=title,
                defaults={
                    "steam_app_id": app_id, "developer": dev, "genre": genre,
                    "metacritic_score": mc, "steam_rating_percent": st,
                    "steam_rating_text": "Extremadamente positivas" if st >= 95 else "Muy positivas",
                    "is_aaa": Decimal(base) >= Decimal("29"), "steam_deck_verified": rank % 3 != 0,
                    "popularity": 1000 - rank * 10,
                },
            )
            game.snapshots.all().delete()
            for i, (store_name, eur) in enumerate(prices.items()):
                price, normal = usd(eur), usd(base)
                Deal.objects.update_or_create(
                    game=game, store=stores[store_name],
                    defaults={
                        "price": price, "normal_price": normal, "currency": "USD",
                        "savings": ((1 - price / normal) * 100).quantize(Decimal("0.01")),
                        "deal_rating": min(Decimal("10"), ((1 - price / normal) * 10 + Decimal(st - 80) / 4)).quantize(Decimal("0.1")),
                        "drm": "Epic" if store_name == "Epic Games Store" else ("GOG" if store_name == "GOG" else "Steam"),
                        "is_on_sale": price < normal,
                        "last_change": now - timedelta(days=(rank * 3 + i) % 20, hours=rank),
                    },
                )
            self._history(game, stores, base, prices, now)
            low = game.snapshots.order_by("price", "recorded_at").first()
            game.cheapest_ever_price, game.cheapest_ever_currency = low.price, "USD"
            game.cheapest_ever_date = low.recorded_at
            game.save()

        msg = f"{len(GAMES)} juegos y {len(STORES)} tiendas de ejemplo cargados."
        if opts.get("user"):
            msg += " " + self._demo_user(opts["user"], opts["password"], now)
        self.stdout.write(self.style.SUCCESS(msg))

    def _history(self, game, stores, base, prices, now):
        best_store, best_eur = min(prices.items(), key=lambda kv: Decimal(kv[1]))
        if game.title == "Hades II":
            points = HADES_HISTORY
        else:
            # En la mitad de los juegos hubo una oferta mejor que la actual (mínimo histórico más bajo)
            sale = Decimal(best_eur) * (Decimal("0.85") if len(game.title) % 2 else 1)
            sale = sale.quantize(Decimal("0.01"))
            mid = ((Decimal(base) + sale) / 2).quantize(Decimal("0.01"))
            points = [(330, base, "Steam"), (250, str(mid), "Steam"), (200, base, "Steam"),
                      (140, str(sale), best_store), (100, base, "Steam"), (60, str(mid), "Steam")]
        for days, eur, store_name in points:
            PriceSnapshot.objects.create(game=game, store=stores.get(store_name, stores["Steam"]),
                                         price=usd(eur), currency="USD", recorded_at=now - timedelta(days=days))
        PriceSnapshot.objects.create(game=game, store=stores[best_store], price=usd(best_eur),
                                     currency="USD", recorded_at=now - timedelta(days=1))

    def _demo_user(self, email, password, now):
        from alerts.models import Notification, PriceAlert

        User = get_user_model()
        user, created = User.objects.get_or_create(
            email=email, defaults={"username": email.split("@")[0], "first_name": "Nico", "last_name": "Demo"}
        )
        user.set_password(password)
        user.save()
        try:
            from allauth.account.models import EmailAddress

            EmailAddress.objects.update_or_create(user=user, email=email,
                                                  defaults={"primary": True, "verified": True})
        except Exception:
            pass
        user.alerts.all().delete()
        user.notifications.all().delete()
        g = {x.title: x for x in Game.objects.all()}
        s = {x.name: x for x in Store.objects.all()}
        demo = [
            ("Elden Ring", "Instant Gaming", "30.00", False),
            ("Baldur's Gate 3", "GOG", "40.00", False),
            ("Red Dead Redemption 2", "Fanatical", "15.00", False),
            ("Cyberpunk 2077", "GOG", "25.00", False),
            ("Hades II", "Steam", "25.00", False),
            ("Balatro", "Steam", "13.00", False),
            ("Stardew Valley", "Steam", "8.00", True),
        ]
        for title, store, target, paused in demo:
            alert = PriceAlert.objects.create(user=user, game=g[title], store=s[store],
                                              target_price=Decimal(target), currency="EUR", is_paused=paused)
            if title in {"Hades II", "Balatro"}:
                days = 18 if title == "Hades II" else 70
                alert.triggered_at = now - timedelta(days=days)
                _, alert.triggered_price = alert.best_deal()
                alert.triggered_store = s[store]
                alert.save()
                Notification.objects.create(
                    user=user, alert=alert, game=g[title],
                    message=f"{title} bajó a {str(alert.triggered_price).replace('.', ',')} € en {store}",
                )
        return f"Cuenta demo: {email} / {password}" if created else f"Cuenta demo actualizada: {email}."
