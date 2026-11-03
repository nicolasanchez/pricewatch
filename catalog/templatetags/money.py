from django import template
from django.conf import settings

from catalog.currency import display_amount, format_money

register = template.Library()


@register.simple_tag(takes_context=True)
def money(context, amount, src=None):
    """Muestra un importe en la moneda del usuario: {% money deal.price deal.currency %}."""
    if amount is None:
        return "—"
    value, cur = display_amount(amount, src or settings.SOURCE_CURRENCY, context.get("currency", "EUR"))
    return format_money(value, cur)


@register.simple_tag(takes_context=True)
def money_value(context, amount, src=None):
    """Igual que money, pero solo el número con punto decimal (para JS y data-*)."""
    if amount is None:
        return ""
    value, _ = display_amount(amount, src or settings.SOURCE_CURRENCY, context.get("currency", "EUR"))
    return f"{value:.2f}"


@register.filter
def pct(value):
    try:
        return f"-{round(float(value))}%"
    except (TypeError, ValueError):
        return ""
