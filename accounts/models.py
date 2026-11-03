from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from catalog.models import CURRENCY_CHOICES, Store

COUNTRY_CHOICES = [
    ("ES", "España"),
    ("PT", "Portugal"),
    ("FR", "Francia"),
    ("IT", "Italia"),
    ("DE", "Alemania"),
    ("GB", "Reino Unido"),
    ("MX", "México"),
    ("XX", "Otro"),
]


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="EUR")
    country = models.CharField(max_length=2, choices=COUNTRY_CHOICES, default="ES")
    email_alerts = models.BooleanField(default=True)
    alert_frequency = models.CharField(
        max_length=10,
        choices=[("instant", "En cuanto baje"), ("daily", "Resumen diario"), ("weekly", "Resumen semanal")],
        default="instant",
    )
    favorite_stores = models.ManyToManyField(Store, blank=True, related_name="fans")

    class Meta:
        verbose_name = "perfil"

    def __str__(self):
        return f"Perfil de {self.user}"

    @property
    def initials(self):
        first, last = self.user.first_name.strip(), self.user.last_name.strip()
        if first or last:
            return ((first[:1] + last[:1]) or first[:2]).upper()
        return (self.user.username or self.user.email or "?")[:2].upper()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
