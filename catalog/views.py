from django.core.paginator import Paginator
from django.db.models import F
from django.shortcuts import get_object_or_404, render

from alerts.forms import AlertForm

from .categories import CATEGORIES, attach_best_deals, games_for, get_category
from .currency import convert
from .models import Game, Store

PAGE_SIZE = 24


def games(request):
    category = get_category(request.GET.get("categoria", "todas"))
    store = None
    if slug := request.GET.get("tienda"):
        store = Store.objects.filter(slug=slug, is_active=True).first()
    q = request.GET.get("q", "").strip()

    page = Paginator(games_for(category, store, q), PAGE_SIZE).get_page(request.GET.get("pagina"))
    items = attach_best_deals(page.object_list, store)
    first_page = page.number == 1
    title = f"Resultados para «{q}»" if q else category.title
    if store:
        title += f" en {store.name}"
    return render(request, "catalog/games.html", {
        "categories": CATEGORIES,
        "category": category,
        "stores": Store.objects.filter(is_active=True, deals__isnull=False).distinct(),
        "store": store,
        "q": q,
        "page": page,
        "top": items[:3] if first_page else [],
        "rest": items[3:] if first_page else items,
        "offset": page.start_index() - 1,
        "title": title,
    })


def best_price_timeline(game, currency):
    """Serie del mejor precio entre tiendas a lo largo del tiempo, en la moneda del usuario."""
    current, points = {}, []
    for snap in game.snapshots.select_related("store").order_by("recorded_at"):
        current[snap.store_id] = (convert(snap.price, snap.currency, currency), snap.store.name)
        best_price, best_store = min(current.values(), key=lambda v: v[0])
        if points and points[-1]["p"] == float(best_price):
            continue
        points.append({"t": snap.recorded_at.isoformat(), "p": float(best_price), "s": best_store})
    return points


def game_detail(request, slug):
    game = get_object_or_404(Game, slug=slug)
    Game.objects.filter(pk=game.pk).update(popularity=F("popularity") + 1)
    currency = request.user.profile.currency if request.user.is_authenticated else "EUR"

    deals = list(game.deals.filter(store__is_active=True).select_related("store").order_by("price"))
    for d in deals:
        d.local_price = convert(d.price, d.currency, currency)
    best = deals[0] if deals else None
    base = max((d.normal_price for d in deals), default=None)
    savings = round((1 - best.price / base) * 100) if best and base else 0

    low_price, low_date = None, None
    if game.cheapest_ever_price is not None:
        low_price, low_date = game.cheapest_ever_price, game.cheapest_ever_date
        low_cur = game.cheapest_ever_currency
    elif (snap := game.historical_low()) is not None:
        low_price, low_date, low_cur = snap.price, snap.recorded_at, snap.currency

    similar = attach_best_deals(
        Game.objects.filter(genre=game.genre).exclude(pk=game.pk).order_by("-popularity")[:4]
        if game.genre else Game.objects.exclude(pk=game.pk).order_by("-popularity")[:4]
    )
    alert_form = AlertForm(game=game, initial={"store": ""})
    return render(request, "catalog/game_detail.html", {
        "game": game,
        "deals": deals,
        "best": best,
        "base_price": base,
        "savings": savings,
        "low_price": low_price,
        "low_currency": low_cur if low_price is not None else None,
        "low_local": convert(low_price, low_cur, currency) if low_price is not None else None,
        "low_date": low_date,
        "timeline": best_price_timeline(game, currency),
        "similar": similar,
        "alert_form": alert_form,
    })
