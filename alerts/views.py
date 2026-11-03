from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from catalog.currency import parse_amount
from catalog.models import Game
from core.context_processors import display_currency

from .forms import AlertForm
from .models import Notification, PriceAlert

TABS = [("activas", "Activas"), ("cumplidas", "Cumplidas"), ("pausadas", "Pausadas")]


def _decorate(alert):
    deal, price = alert.best_deal()
    alert.current_deal, alert.current_price = deal, price
    alert.bucket = alert.status(price)
    if alert.bucket == "pausadas":
        alert.note = "Caducada" if alert.is_expired else "Pausada por ti"
    elif alert.bucket == "cumplidas":
        alert.note = (f"Bajó el {timezone.localtime(alert.triggered_at):%d/%m/%Y}"
                      if alert.triggered_at else "Ya está por debajo de tu objetivo")
    else:
        alert.missing = price - alert.target_price if price is not None else None
        alert.note = None
    return alert


def _panel_context(request, tab, **extra):
    alerts = [
        _decorate(a)
        for a in PriceAlert.objects.alive().filter(user=request.user)
        .select_related("game", "store").prefetch_related("game__deals__store")
    ]
    counts = {key: 0 for key, _ in TABS}
    for a in alerts:
        counts[a.bucket] += 1
    tab = tab if tab in counts else "activas"
    return {
        "tab": tab,
        "tabs": [(key, label, counts[key]) for key, label in TABS],
        "alerts": [a for a in alerts if a.bucket == tab],
        **extra,
    }


def _panel(request, tab, **extra):
    return render(request, "alerts/_panel.html", _panel_context(request, tab, **extra))


@login_required
def alert_list(request):
    ctx = _panel_context(request, request.GET.get("tab", "activas"))
    if request.headers.get("HX-Request"):
        return render(request, "alerts/_panel.html", ctx)
    return render(request, "alerts/list.html", ctx)


@login_required
@require_POST
def create(request, slug):
    game = get_object_or_404(Game, slug=slug)
    form = AlertForm(request.POST, game=game)
    if form.is_valid():
        alert = form.save(request.user, display_currency(request))
        return render(request, "alerts/_created.html", {"alert": _decorate(alert), "game": game})
    return render(request, "catalog/_alert_form.html", {"alert_form": form, "game": game}, status=422)


def _own(request, pk):
    return get_object_or_404(PriceAlert.objects.alive(), pk=pk, user=request.user)


@login_required
def row(request, pk):
    return render(request, "alerts/_row.html", {"a": _decorate(_own(request, pk)), "tab": request.GET.get("tab")})


@login_required
def edit(request, pk):
    alert = _decorate(_own(request, pk))
    return render(request, "alerts/_row.html", {"a": alert, "editing": True, "tab": request.GET.get("tab"),
                                               "draft": f"{alert.target_price:.2f}".replace(".", ",")})


@login_required
@require_POST
def save_target(request, pk):
    alert = _own(request, pk)
    tab = request.POST.get("tab", "activas")
    value = parse_amount(request.POST.get("target_price"))
    if value is None:
        a = _decorate(alert)
        return render(request, "alerts/_row.html", {"a": a, "editing": True, "tab": tab, "error": True,
                                                   "draft": request.POST.get("target_price", "")})
    alert.target_price = value
    alert.triggered_at = None  # objetivo nuevo: volveremos a avisar cuando se cumpla
    alert.triggered_price = None
    alert.save(update_fields=["target_price", "triggered_at", "triggered_price", "updated_at"])
    response = _panel(request, tab, flash=f"Objetivo de {alert.game.title} actualizado.")
    response["HX-Retarget"] = "#alerts-panel"
    response["HX-Reswap"] = "outerHTML"
    return response


@login_required
@require_POST
def toggle_pause(request, pk):
    alert = _own(request, pk)
    alert.is_paused = not alert.is_paused
    if not alert.is_paused and alert.is_expired:
        alert.expires_at = None
    alert.save(update_fields=["is_paused", "expires_at", "updated_at"])
    return _panel(request, request.POST.get("tab", "activas"))


@login_required
@require_POST
def delete(request, pk):
    alert = _own(request, pk)
    alert.deleted_at = timezone.now()
    alert.save(update_fields=["deleted_at", "updated_at"])
    return _panel(request, request.POST.get("tab", "activas"), undo=alert)


@login_required
@require_POST
def undo(request, pk):
    alert = get_object_or_404(PriceAlert, pk=pk, user=request.user, deleted_at__isnull=False)
    alert.deleted_at = None
    alert.save(update_fields=["deleted_at", "updated_at"])
    return _panel(request, request.POST.get("tab", "activas"))


@login_required
@require_POST
def mark_read(request):
    Notification.objects.filter(user=request.user, read_at__isnull=True).update(read_at=timezone.now())
    return HttpResponse(status=204)
