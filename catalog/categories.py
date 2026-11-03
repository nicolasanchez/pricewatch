"""Categorías de la pestaña Juegos.

Todas salen de los filtros y órdenes que ofrece la API de CheapShark
(sortBy, upperPrice, metacritic, steamRating, AAA, steamworks), aplicados
sobre los datos que ya tenemos guardados.
"""
from dataclasses import dataclass, field
from decimal import Decimal

from django.conf import settings
from django.db.models import Count, Max, Min, Q

from .currency import convert
from .models import Game

ICONS = {
    "all": "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
    "deal": "M3 12V4h8l10 10-8 8zM7.5 7.5h.01",
    "pct": "M19 5L5 19M6.5 9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM17.5 20a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z",
    "low": "M12 4v16M6 14l6 6 6-6",
    "eur": "M17 7a6 6 0 1 0 0 10M5 10h8M5 14h8",
    "star": "M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.5 2.9 1-6.1L3.2 9.5l6.1-.9z",
    "thumb": "M7 10v11H3V10zM7 10l4-8a3 3 0 0 1 3 3v4h6a2 2 0 0 1 2 2.3l-1.4 8A2 2 0 0 1 18.6 21H7",
    "crown": "M3 18h18M4 8l4 4 4-7 4 7 4-4-2 10H6z",
    "clock": "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2",
    "key": "M14 10a4 4 0 1 0 0-.01M11.2 12.8L3 21M6 18l2 2M9 15l2 2",
}


@dataclass(frozen=True)
class Category:
    key: str
    name: str
    caption: str
    title: str
    icon: str
    description: str = ""
    on_home: bool = False
    extra: dict = field(default_factory=dict)


CATEGORIES = [
    Category("todas", "Todos", "Por popularidad", "Populares ahora", ICONS["all"]),
    Category("ofertas", "Mejores ofertas", "Precio y valoración", "Mejores ofertas", ICONS["deal"],
             "El mejor equilibrio entre rebaja y valoración.", on_home=True),
    Category("descuento", "Mayor descuento", "Ordenado por % de rebaja", "Mayor descuento", ICONS["pct"],
             "Ordenados por el porcentaje de rebaja.", on_home=True),
    Category("baratos", "Precio más bajo", "De menor a mayor", "Precio más bajo", ICONS["low"]),
    Category("menos-5", "Menos de 5 €", "Precio máximo 5 €", "Menos de 5 €", ICONS["eur"],
             "Buenas reseñas por menos que un café y un bocadillo.", on_home=True, extra={"max_eur": 5}),
    Category("menos-15", "Menos de 15 €", "Precio máximo 15 €", "Menos de 15 €", ICONS["eur"],
             extra={"max_eur": 15}),
    Category("metacritic", "Nota alta en Metacritic", "90 o más", "Nota alta en Metacritic", ICONS["star"],
             "Juegos con 90 o más de la crítica.", on_home=True),
    Category("steam", "Muy valorados en Steam", "95 % o más positivas", "Muy valorados en Steam", ICONS["thumb"],
             "Con un 95 % o más de reseñas positivas.", on_home=True),
    Category("aaa", "AAA rebajados", "Grandes estudios", "AAA rebajados", ICONS["crown"],
             "Grandes producciones con descuento.", on_home=True),
    Category("recientes", "Recién rebajados", "Ofertas más nuevas", "Recién rebajados", ICONS["clock"]),
    Category("steamworks", "Se activan en Steam", "Clave para tu biblioteca", "Se activan en Steam", ICONS["key"]),
]
BY_KEY = {c.key: c for c in CATEGORIES}


def get_category(key):
    return BY_KEY.get(key) or BY_KEY["todas"]


def home_categories():
    return [c for c in CATEGORIES if c.on_home]


def annotated_games(store=None):
    """Juegos con su mejor precio, rebaja, valoración y última bajada, opcionalmente en una tienda."""
    deal_q = Q(deals__store__is_active=True)
    if store is not None:
        deal_q &= Q(deals__store=store)
    return (
        Game.objects.annotate(
            best_price=Min("deals__price", filter=deal_q),
            normal=Max("deals__normal_price", filter=deal_q),
            best_savings=Max("deals__savings", filter=deal_q),
            rating=Max("deals__deal_rating", filter=deal_q),
            latest_change=Max("deals__last_change", filter=deal_q),
            steam_keys=Count("deals", filter=deal_q & Q(deals__drm__iexact="Steam")),
        )
        .filter(best_price__isnull=False)
    )


def games_for(category, store=None, query=None):
    qs = annotated_games(store)
    if query:
        qs = qs.filter(title__icontains=query.strip())
    k = category.key
    if k in {"menos-5", "menos-15"}:
        limit = convert(Decimal(category.extra["max_eur"]), "EUR", settings.SOURCE_CURRENCY)
        qs = qs.filter(best_price__lte=limit)
        order = ["best_price"] if k == "menos-5" else ["-popularity", "best_price"]
    elif k == "ofertas":
        order = ["-rating", "-best_savings"]
    elif k == "descuento":
        order = ["-best_savings", "best_price"]
    elif k == "baratos":
        order = ["best_price"]
    elif k == "metacritic":
        qs = qs.filter(metacritic_score__gte=90)
        order = ["-metacritic_score"]
    elif k == "steam":
        qs = qs.filter(steam_rating_percent__gte=95)
        order = ["-steam_rating_percent", "-popularity"]
    elif k == "aaa":
        qs = qs.filter(is_aaa=True)
        order = ["-best_savings"]
    elif k == "recientes":
        order = ["-latest_change"]
    elif k == "steamworks":
        qs = qs.filter(steam_keys__gt=0)
        order = ["-popularity"]
    else:
        order = ["-popularity", "-rating"]
    return qs.order_by(*order, "title")


def attach_best_deals(games, store=None):
    """Añade a cada juego `best_deal` (la oferta más barata) sin consultas por juego."""
    from .models import Deal

    games = list(games)
    deals = Deal.objects.filter(game__in=games, store__is_active=True).select_related("store")
    if store is not None:
        deals = deals.filter(store=store)
    cheapest = {}
    for deal in deals.order_by("price"):
        cheapest.setdefault(deal.game_id, deal)
    for game in games:
        game.best_deal = cheapest.get(game.pk)
        game.is_historical_low = bool(
            game.best_deal and game.cheapest_ever_price is not None
            and game.best_deal.price <= game.cheapest_ever_price
        )
    return games
