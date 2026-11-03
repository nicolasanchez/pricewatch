from datetime import timedelta

from django import forms
from django.utils import timezone

from catalog.currency import parse_amount
from catalog.models import Store

from .models import PriceAlert


class AlertForm(forms.Form):
    store = forms.ModelChoiceField(queryset=Store.objects.none(), required=False, empty_label="Cualquier tienda")
    target_price = forms.CharField(label="Avísame cuando baje de", max_length=20)
    notify_historical_low = forms.BooleanField(required=False, initial=True,
                                               label="Avisarme también si llega a su mínimo histórico")
    official_only = forms.BooleanField(required=False, label="Solo claves de tiendas oficiales")
    channel = forms.ChoiceField(choices=PriceAlert.CHANNELS, initial="email", label="Avisar por")
    expiry = forms.TypedChoiceField(choices=PriceAlert.EXPIRY_CHOICES, coerce=int, initial=0, label="Caducidad")

    def __init__(self, *args, game=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.game = game
        if game is not None:
            self.fields["store"].queryset = Store.objects.filter(deals__game=game, is_active=True).distinct()

    def clean_target_price(self):
        value = parse_amount(self.cleaned_data["target_price"])
        if value is None:
            raise forms.ValidationError("Pon un precio válido, por ejemplo 19,99.")
        return value

    def save(self, user, currency):
        data = self.cleaned_data
        months = data["expiry"]
        return PriceAlert.objects.create(
            user=user, game=self.game, store=data["store"], target_price=data["target_price"],
            currency=currency, notify_historical_low=data["notify_historical_low"],
            official_only=data["official_only"], channel=data["channel"],
            expires_at=timezone.now() + timedelta(days=30 * months) if months else None,
        )
