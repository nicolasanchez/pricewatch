from django import forms

from catalog.models import CURRENCY_CHOICES, Store

from .models import COUNTRY_CHOICES, Profile


class SignupExtraForm(forms.Form):
    """Campos extra del registro (allauth los añade a su formulario)."""

    first_name = forms.CharField(label="Nombre", max_length=60, required=False)
    last_name = forms.CharField(label="Apellidos", max_length=100, required=False)
    country = forms.ChoiceField(label="País", choices=COUNTRY_CHOICES, initial="ES")
    currency = forms.ChoiceField(label="Moneda", choices=CURRENCY_CHOICES, initial="EUR")
    favorite_stores = forms.ModelMultipleChoiceField(
        label="Tiendas en las que sueles comprar",
        queryset=Store.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    email_alerts = forms.BooleanField(label="Quiero recibir por correo los avisos de mis alertas.",
                                      required=False, initial=True)
    accept_terms = forms.BooleanField(label="Acepto los términos de uso y la política de privacidad.",
                                      required=True,
                                      error_messages={"required": "Tienes que aceptar los términos para crear la cuenta."})

    def signup(self, request, user):
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.save()
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.country = self.cleaned_data["country"]
        profile.currency = self.cleaned_data["currency"]
        profile.email_alerts = self.cleaned_data.get("email_alerts", False)
        profile.save()
        profile.favorite_stores.set(self.cleaned_data.get("favorite_stores") or [])


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre", max_length=60, required=False)
    last_name = forms.CharField(label="Apellidos", max_length=100, required=False)

    class Meta:
        model = Profile
        fields = ["currency", "country", "email_alerts", "alert_frequency", "favorite_stores"]
        labels = {
            "currency": "Moneda en la que ves los precios",
            "country": "País",
            "email_alerts": "Recibir avisos por correo",
            "alert_frequency": "Frecuencia de los avisos",
            "favorite_stores": "Tiendas en las que sueles comprar",
        }
        widgets = {"favorite_stores": forms.CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["favorite_stores"].queryset = Store.objects.filter(is_active=True)
        user = self.instance.user
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name

    def save(self, commit=True):
        profile = super().save(commit)
        user = profile.user
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.save(update_fields=["first_name", "last_name"])
        return profile
