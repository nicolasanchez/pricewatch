from django.conf import settings

from catalog.currency import SYMBOLS


def display_currency(request):
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        profile = getattr(user, "profile", None)
        if profile is not None:
            return profile.currency
    return settings.DEFAULT_CURRENCY


def site(request):
    currency = display_currency(request)
    ctx = {
        "currency": currency,
        "currency_symbol": SYMBOLS.get(currency, currency),
        "google_enabled": "google" in settings.SOCIALACCOUNT_PROVIDERS,
        "apple_enabled": "apple" in settings.SOCIALACCOUNT_PROVIDERS,
        "contact_email": settings.CONTACT_EMAIL,
        "nav": getattr(request, "resolver_match", None) and request.resolver_match.namespace,
    }
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        from alerts.models import Notification

        notes = Notification.objects.filter(user=user).select_related("game")[:6]
        ctx["header_notifications"] = notes
        ctx["unread_count"] = Notification.objects.filter(user=user, read_at__isnull=True).count()
    return ctx
