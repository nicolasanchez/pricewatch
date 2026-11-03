"""Clientes de las APIs externas y lógica de sincronización.

- CheapShark: tiendas, ofertas y precio mínimo histórico (precios en USD).
- Frankfurter: tipos de cambio diarios del Banco Central Europeo (base EUR).
"""
import logging
import time
from datetime import datetime, timezone as dt_tz
from decimal import Decimal

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .currency import clear_rates_cache
from .models import CURRENCY_CHOICES, Deal, ExchangeRate, Game, PriceSnapshot, Store

log = logging.getLogger(__name__)
HEADERS = {"User-Agent": "PriceWatch/1.0 (comparador de precios; proyecto de portfolio)"}
AAA_RETAIL_THRESHOLD = Decimal("29.00")  # mismo criterio que el filtro AAA de CheapShark


class ApiError(Exception):
    pass


def _get(url, params=None, retries=3):
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
        except requests.RequestException as exc:
            if attempt == retries - 1:
                raise ApiError(f"No se pudo conectar con {url}: {exc}") from exc
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code == 429:  # límite de peticiones: esperamos y reintentamos
            time.sleep(int(resp.headers.get("Retry-After", 5 * (attempt + 1))))
            continue
        if resp.status_code >= 400:
            raise ApiError(f"{url} respondió {resp.status_code}")
        return resp.json()
    raise ApiError(f"{url}: demasiados reintentos")


def _ts(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(value, tz=dt_tz.utc) if value > 0 else None


def _int(value):
    try:
        return int(value) or None
    except (TypeError, ValueError):
        return None


# --- CheapShark -----------------------------------------------------------

class CheapShark:
    def __init__(self, base_url=None):
        self.base = (base_url or settings.CHEAPSHARK_BASE_URL).rstrip("/")

    def stores(self):
        return _get(f"{self.base}/stores")

    def deals(self, page=0, page_size=60, **params):
        return _get(f"{self.base}/deals", {"pageNumber": page, "pageSize": page_size, **params})

    def games(self, ids):
        return _get(f"{self.base}/games", {"ids": ",".join(str(i) for i in ids)})


def sync_stores(client=None):
    client = client or CheapShark()
    created = 0
    for row in client.stores():
        logo = (row.get("images") or {}).get("logo", "")
        store, was_created = Store.objects.update_or_create(
            cheapshark_id=int(row["storeID"]),
            defaults={
                "name": row["storeName"],
                "is_active": bool(int(row.get("isActive", 1))),
                "logo_url": f"https://www.cheapshark.com{logo}" if logo else "",
            },
        )
        created += was_created
    return created


def _upsert_game(cheapshark_game_id, title, **extra):
    game = Game.objects.filter(cheapshark_game_id=cheapshark_game_id).first()
    if game is None:
        game = Game(cheapshark_game_id=cheapshark_game_id, title=title)
    for key, value in extra.items():
        if value not in (None, ""):
            setattr(game, key, value)
    game.save()
    return game


def _upsert_deal(game, store, deal_id, price, normal, savings, rating=None, on_sale=None, last_change=None):
    now = timezone.now()
    deal = Deal.objects.filter(game=game, store=store).first()
    price_changed = deal is None or deal.price != price
    if deal is None:
        deal = Deal(game=game, store=store)
    deal.cheapshark_deal_id = deal_id or deal.cheapshark_deal_id
    deal.price, deal.normal_price, deal.savings = price, normal, savings
    deal.currency = settings.SOURCE_CURRENCY
    deal.is_on_sale = on_sale if on_sale is not None else price < normal
    if rating is not None:
        deal.deal_rating = rating
    if price_changed:
        deal.last_change = last_change or now
    deal.save()
    if price_changed:
        PriceSnapshot.objects.create(game=game, store=store, price=price, currency=deal.currency,
                                     recorded_at=last_change or now)
    return price_changed


@transaction.atomic
def import_deals(rows):
    """Guarda una lista de ofertas con el formato de /deals. Devuelve cuántos precios cambiaron."""
    stores = {s.cheapshark_id: s for s in Store.objects.all()}
    changed = 0
    for row in rows:
        store = stores.get(int(row["storeID"]))
        if store is None:
            continue
        normal = Decimal(row["normalPrice"])
        released = _ts(row.get("releaseDate"))
        game = _upsert_game(
            int(row["gameID"]), row["title"],
            steam_app_id=_int(row.get("steamAppID")),
            thumbnail_url=row.get("thumb", ""),
            metacritic_score=_int(row.get("metacriticScore")),
            steam_rating_percent=_int(row.get("steamRatingPercent")),
            steam_rating_text=row.get("steamRatingText") or "",
            release_date=released.date() if released else None,
            is_aaa=normal >= AAA_RETAIL_THRESHOLD,
        )
        changed += _upsert_deal(
            game, store, row.get("dealID"),
            Decimal(row["salePrice"]), normal, Decimal(row.get("savings") or 0),
            rating=Decimal(row["dealRating"]) if row.get("dealRating") else None,
            on_sale=bool(int(row.get("isOnSale", 0))),
            last_change=_ts(row.get("lastChange")),
        )
    return changed


def sync_deals(pages=3, page_size=60, client=None, **params):
    client = client or CheapShark()
    total = 0
    for page in range(pages):
        rows = client.deals(page=page, page_size=page_size, **params)
        if not rows:
            break
        total += import_deals(rows)
        time.sleep(1)  # ser amables con la API
    return total


@transaction.atomic
def refresh_games(games, client=None):
    """Actualiza todas las tiendas y el mínimo histórico de unos juegos concretos (máx. 25 por llamada)."""
    client = client or CheapShark()
    games = [g for g in games if g.cheapshark_game_id]
    stores = {s.cheapshark_id: s for s in Store.objects.all()}
    changed = 0
    for i in range(0, len(games), 25):
        chunk = games[i:i + 25]
        data = client.games([g.cheapshark_game_id for g in chunk])
        for game in chunk:
            info = data.get(str(game.cheapshark_game_id)) or {}
            ever = info.get("cheapestPriceEver") or {}
            if ever.get("price"):
                game.cheapest_ever_price = Decimal(ever["price"])
                game.cheapest_ever_currency = settings.SOURCE_CURRENCY
                game.cheapest_ever_date = _ts(ever.get("date"))
                game.save(update_fields=["cheapest_ever_price", "cheapest_ever_currency", "cheapest_ever_date"])
            for row in info.get("deals", []):
                store = stores.get(int(row["storeID"]))
                if store is None:
                    continue
                changed += _upsert_deal(
                    game, store, row.get("dealID"),
                    Decimal(row["price"]), Decimal(row["retailPrice"]), Decimal(row.get("savings") or 0),
                )
        time.sleep(1)
    return changed


# --- Tipos de cambio -------------------------------------------------------

def sync_rates(base_url=None):
    base = (base_url or settings.RATES_BASE_URL).rstrip("/")
    wanted = [code for code, _ in CURRENCY_CHOICES if code != "EUR"]
    data = _get(f"{base}/latest", {"from": "EUR", "to": ",".join(wanted)})
    day = datetime.strptime(data["date"], "%Y-%m-%d").date()
    saved = 0
    for code, rate in data.get("rates", {}).items():
        ExchangeRate.objects.update_or_create(currency=code, date=day, defaults={"rate": Decimal(str(rate))})
        saved += 1
    clear_rates_cache()
    return saved, day
