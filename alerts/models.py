from django.conf import settings
from django.db import models
from django.utils import timezone

from catalog.currency import convert
from catalog.models import CURRENCY_CHOICES, Game, Store


class AlertQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)


class PriceAlert(models.Model):
    """Alerta de precio. El objetivo se guarda en la moneda del usuario al crearla."""

    CHANNELS = [("email", "Correo"), ("email_web", "Correo y aviso en la web")]
    EXPIRY_CHOICES = [(0, "Sin caducidad"), (1, "1 mes"), (3, "3 meses"), (6, "6 meses")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alerts")
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="alerts")
    store = models.ForeignKey(
        Store, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Vacío = cualquier tienda.",
    )
    target_price = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="EUR")
    notify_historical_low = models.BooleanField(default=True)
    official_only = models.BooleanField(default=False)
    channel = models.CharField(max_length=10, choices=CHANNELS, default="email")
    expires_at = models.DateTimeField(null=True, blank=True)
    is_paused = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(null=True, blank=True)
    triggered_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    triggered_store = models.ForeignKey(
        Store, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AlertQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "alerta de precio"
        verbose_name_plural = "alertas de precio"

    def __str__(self):
        return f"{self.user} · {self.game} < {self.target_price} {self.currency}"

    # --- Precio actual en la moneda de la alerta ---
    def matching_deals(self):
        deals = self.game.deals.select_related("store").filter(store__is_active=True)
        if self.store_id:
            deals = deals.filter(store_id=self.store_id)
        if self.official_only:
            deals = deals.filter(store__is_official=True)
        return deals

    def best_deal(self):
        best, best_price = None, None
        for deal in self.matching_deals():
            price = convert(deal.price, deal.currency, self.currency)
            if best_price is None or price < best_price:
                best, best_price = deal, price
        return best, best_price

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at < timezone.now())

    def status(self, current_price=None):
        if self.is_paused or self.is_expired:
            return "pausadas"
        if current_price is None:
            _, current_price = self.best_deal()
        if current_price is not None and current_price <= self.target_price:
            return "cumplidas"
        return "activas"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    alert = models.ForeignKey(PriceAlert, on_delete=models.SET_NULL, null=True, blank=True)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "aviso"

    def __str__(self):
        return self.message
