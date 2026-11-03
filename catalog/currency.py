"""Conversión y formato de precios.

Los tipos de cambio se guardan con base EUR (1 EUR = rate unidades). Para pasar
de una moneda a otra: importe / rate[origen] * rate[destino].
"""
from decimal import ROUND_HALF_UP, Decimal

from django.core.cache import cache

SYMBOLS = {
    "EUR": "€", "USD": "US$", "GBP": "£", "CHF": "CHF",
    "SEK": "kr", "PLN": "zł", "MXN": "MX$", "BRL": "R$",
}
CACHE_KEY = "pricewatch:rates"
CENT = Decimal("0.01")


def latest_rates():
    """Último tipo de cambio de cada moneda (EUR siempre vale 1)."""
    rates = cache.get(CACHE_KEY)
    if rates is None:
        from catalog.models import ExchangeRate

        rates = {"EUR": Decimal("1")}
        for currency, rate in ExchangeRate.objects.order_by("currency", "-date").values_list("currency", "rate"):
            rates.setdefault(currency, rate)
        cache.set(CACHE_KEY, rates, 60 * 10)
    return rates


def clear_rates_cache():
    cache.delete(CACHE_KEY)


def can_convert(src, dst):
    rates = latest_rates()
    return src == dst or (src in rates and dst in rates)


def convert(amount, src, dst):
    """Convierte un importe. Si falta un tipo de cambio, lo devuelve sin convertir."""
    if amount is None:
        return None
    amount = Decimal(str(amount))
    if src == dst:
        return amount.quantize(CENT, ROUND_HALF_UP)
    rates = latest_rates()
    if src not in rates or dst not in rates:
        return amount.quantize(CENT, ROUND_HALF_UP)
    return (amount / rates[src] * rates[dst]).quantize(CENT, ROUND_HALF_UP)


def display_amount(amount, src, dst):
    """Devuelve (importe, moneda) listos para mostrar, cayendo a la moneda original si no hay tipo."""
    if amount is None:
        return None, dst
    if can_convert(src, dst):
        return convert(amount, src, dst), dst
    return Decimal(str(amount)).quantize(CENT, ROUND_HALF_UP), src


def format_money(amount, currency):
    if amount is None:
        return "—"
    amount = Decimal(str(amount)).quantize(CENT, ROUND_HALF_UP)
    integer, _, cents = f"{amount:,.2f}".partition(".")
    integer = integer.replace(",", ".")
    return f"{integer},{cents} {SYMBOLS.get(currency, currency)}"


def parse_amount(text):
    """Acepta '24,99', '24.99', '24,99 €' o '1.024,50'. Devuelve Decimal o None."""
    if text is None:
        return None
    cleaned = str(text).strip()
    for symbol in list(SYMBOLS.values()) + ["€", "$"]:
        cleaned = cleaned.replace(symbol, "")
    cleaned = cleaned.replace(" ", "")
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        value = Decimal(cleaned)
    except Exception:
        return None
    if value <= 0 or value > Decimal("100000"):
        return None
    return value.quantize(CENT, ROUND_HALF_UP)
