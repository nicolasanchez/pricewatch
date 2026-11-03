"""Comprobación de alertas y envío de avisos."""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from catalog.currency import convert, format_money

from .models import Notification, PriceAlert

log = logging.getLogger(__name__)


def _should_notify(alert, price):
    """Solo avisamos la primera vez que se cumple o si después baja todavía más."""
    if alert.triggered_at is None:
        return True
    return alert.triggered_price is not None and price < alert.triggered_price


def check_alert(alert):
    """Devuelve la notificación creada o None."""
    if alert.is_paused or alert.deleted_at or alert.is_expired:
        return None
    deal, price = alert.best_deal()
    if deal is None:
        return None
    game = alert.game
    reached = price <= alert.target_price
    low_hit = False
    if not reached and alert.notify_historical_low and game.cheapest_ever_price is not None:
        low = convert(game.cheapest_ever_price, game.cheapest_ever_currency, alert.currency)
        low_hit = price <= low
    if not (reached or low_hit) or not _should_notify(alert, price):
        return None

    alert.triggered_at = timezone.now()
    alert.triggered_price = price
    alert.triggered_store = deal.store
    alert.save(update_fields=["triggered_at", "triggered_price", "triggered_store", "updated_at"])

    reason = "" if reached else " (mínimo histórico)"
    message = f"{game.title} bajó a {format_money(price, alert.currency)} en {deal.store.name}{reason}"
    notification = Notification.objects.create(user=alert.user, alert=alert, game=game, message=message)

    profile = getattr(alert.user, "profile", None)
    if profile and profile.email_alerts and profile.alert_frequency == "instant" and alert.user.email:
        url = settings.SITE_URL.rstrip("/") + reverse("catalog:game", args=[game.slug])
        send_mail(
            subject=f"PriceWatch: {game.title} ya está a {format_money(price, alert.currency)}",
            message=(
                f"Hola,\n\n{message}.\nTu objetivo era {format_money(alert.target_price, alert.currency)}.\n\n"
                f"Ver el juego: {url}\nComprar: {deal.redirect_url}\n\n"
                "Puedes pausar o editar tus alertas en PriceWatch > Mis alertas."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[alert.user.email],
            fail_silently=True,
        )
    return notification


def check_all_alerts():
    alerts = PriceAlert.objects.alive().filter(is_paused=False).select_related("game", "user", "user__profile")
    return [n for n in (check_alert(a) for a in alerts) if n]


def send_digests(period):
    """Envía un resumen con los avisos del periodo a quien lo prefiera así."""
    since = timezone.now() - timedelta(days=1 if period == "daily" else 7)
    sent = 0
    pending = (
        Notification.objects.filter(created_at__gte=since, user__profile__alert_frequency=period,
                                    user__profile__email_alerts=True)
        .select_related("user")
        .order_by("user_id", "-created_at")
    )
    by_user = {}
    for n in pending:
        by_user.setdefault(n.user, []).append(n.message)
    for user, messages in by_user.items():
        if not user.email:
            continue
        send_mail(
            subject=f"PriceWatch: {len(messages)} bajada(s) de precio",
            message="Resumen de tus alertas:\n\n" + "\n".join(f"· {m}" for m in messages),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        sent += 1
    return sent
