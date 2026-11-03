from decimal import Decimal

from django.db import models
from django.urls import reverse
from django.utils.text import slugify

CURRENCY_CHOICES = [
    ("EUR", "Euro (€)"),
    ("USD", "Dólar estadounidense (US$)"),
    ("GBP", "Libra esterlina (£)"),
    ("CHF", "Franco suizo (CHF)"),
    ("SEK", "Corona sueca (kr)"),
    ("PLN", "Esloti polaco (zł)"),
    ("MXN", "Peso mexicano (MX$)"),
    ("BRL", "Real brasileño (R$)"),
]


class Store(models.Model):
    """Tienda de la que obtenemos precios (CheapShark /stores)."""

    cheapshark_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, unique=True)
    website = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    is_official = models.BooleanField(
        default=True, help_text="Desmárcalo para tiendas de claves de revendedores."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "tienda"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Game(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    cheapshark_game_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    steam_app_id = models.PositiveIntegerField(null=True, blank=True)
    thumbnail_url = models.URLField(blank=True)
    developer = models.CharField(max_length=120, blank=True)
    genre = models.CharField(max_length=80, blank=True)
    release_date = models.DateField(null=True, blank=True)
    metacritic_score = models.PositiveSmallIntegerField(null=True, blank=True)
    steam_rating_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    steam_rating_text = models.CharField(max_length=60, blank=True)
    is_aaa = models.BooleanField(default=False)
    steam_deck_verified = models.BooleanField(default=False)
    cheapest_ever_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    cheapest_ever_currency = models.CharField(max_length=3, default="USD")
    cheapest_ever_date = models.DateTimeField(null=True, blank=True)
    popularity = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        verbose_name = "juego"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "juego"
            slug, n = base, 2
            while Game.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:game", args=[self.slug])

    @property
    def header_image(self):
        if self.steam_app_id:
            return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{self.steam_app_id}/header.jpg"
        return self.thumbnail_url

    def historical_low(self):
        return self.snapshots.order_by("price", "recorded_at").first()


class Deal(models.Model):
    """Precio actual de un juego en una tienda (una fila por pareja juego-tienda)."""

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="deals")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="deals")
    cheapshark_deal_id = models.CharField(max_length=120, unique=True, null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    normal_price = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    savings = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    deal_rating = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    drm = models.CharField(max_length=40, default="Steam")
    is_on_sale = models.BooleanField(default=False)
    last_change = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["price"]
        constraints = [models.UniqueConstraint(fields=["game", "store"], name="unique_deal_per_store")]
        indexes = [models.Index(fields=["price"]), models.Index(fields=["-savings"])]
        verbose_name = "oferta"

    def __str__(self):
        return f"{self.game} en {self.store}: {self.price} {self.currency}"

    @property
    def redirect_url(self):
        if self.cheapshark_deal_id:
            return f"https://www.cheapshark.com/redirect?dealID={self.cheapshark_deal_id}"
        return self.store.website


class PriceSnapshot(models.Model):
    """Histórico: se guarda una fila cada vez que cambia el precio en una tienda."""

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="snapshots")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="snapshots")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    recorded_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["recorded_at"]
        indexes = [models.Index(fields=["game", "recorded_at"])]
        verbose_name = "precio histórico"
        verbose_name_plural = "histórico de precios"

    def __str__(self):
        return f"{self.game} · {self.store} · {self.price} ({self.recorded_at:%d/%m/%Y})"


class ExchangeRate(models.Model):
    """Tipos de cambio con base EUR: 1 EUR = rate unidades de `currency`."""

    currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=14, decimal_places=6)
    date = models.DateField()

    class Meta:
        ordering = ["-date", "currency"]
        constraints = [models.UniqueConstraint(fields=["currency", "date"], name="unique_rate_per_day")]
        verbose_name = "tipo de cambio"
        verbose_name_plural = "tipos de cambio"

    def __str__(self):
        return f"1 EUR = {self.rate} {self.currency} ({self.date})"
