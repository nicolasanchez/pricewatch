from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import TestCase

from alerts.models import Notification, PriceAlert
from alerts.services import check_all_alerts
from catalog.currency import clear_rates_cache
from catalog.models import Game, Store


class AlertFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=mock.MagicMock())
        cls.user = get_user_model().objects.create_user("ana", "ana@example.com", "clave-segura-123")

    def setUp(self):
        clear_rates_cache()
        self.client.force_login(self.user)
        self.game = Game.objects.get(title="Hades II")

    def test_create_alert_from_modal(self):
        resp = self.client.post(f"/alertas/crear/{self.game.slug}/", {
            "store": "", "target_price": "19,99", "notify_historical_low": "on", "channel": "email", "expiry": "3",
        })
        self.assertContains(resp, "Alerta creada")
        alert = PriceAlert.objects.get(user=self.user)
        self.assertEqual(alert.target_price, Decimal("19.99"))
        self.assertEqual(alert.currency, "EUR")
        self.assertIsNotNone(alert.expires_at)

    def test_invalid_price_shows_error(self):
        resp = self.client.post(f"/alertas/crear/{self.game.slug}/", {"target_price": "gratis", "channel": "email", "expiry": "0"})
        self.assertEqual(resp.status_code, 422)
        self.assertContains(resp, "precio válido", status_code=422)

    def test_inline_edit_pause_delete_undo(self):
        alert = PriceAlert.objects.create(user=self.user, game=self.game, target_price=Decimal("10"), currency="EUR")
        self.assertContains(self.client.get(f"/alertas/{alert.pk}/editar/"), 'name="target_price"')
        self.client.post(f"/alertas/{alert.pk}/objetivo/", {"target_price": "25,50", "tab": "activas"})
        alert.refresh_from_db()
        self.assertEqual(alert.target_price, Decimal("25.50"))
        self.assertEqual(alert.status(), "cumplidas")  # 23,99 € ya está por debajo

        self.client.post(f"/alertas/{alert.pk}/pausar/", {"tab": "cumplidas"})
        alert.refresh_from_db()
        self.assertTrue(alert.is_paused)

        resp = self.client.post(f"/alertas/{alert.pk}/eliminar/", {"tab": "pausadas"})
        self.assertContains(resp, "Deshacer")
        self.assertFalse(PriceAlert.objects.alive().filter(pk=alert.pk).exists())
        self.client.post(f"/alertas/{alert.pk}/deshacer/", {"tab": "pausadas"})
        self.assertTrue(PriceAlert.objects.alive().filter(pk=alert.pk).exists())

    def test_other_users_alerts_are_private(self):
        other = get_user_model().objects.create_user("eve", "eve@example.com", "otra-clave-123")
        alert = PriceAlert.objects.create(user=other, game=self.game, target_price=Decimal("10"))
        self.assertEqual(self.client.post(f"/alertas/{alert.pk}/eliminar/").status_code, 404)

    def test_check_alerts_notifies_once(self):
        PriceAlert.objects.create(user=self.user, game=self.game, target_price=Decimal("30"), currency="EUR",
                                  store=Store.objects.get(name="Steam"))
        self.assertEqual(len(check_all_alerts()), 1)
        self.assertEqual(len(check_all_alerts()), 0)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Hades II", mail.outbox[0].subject)

    def test_user_currency_changes_display(self):
        self.user.profile.currency = "GBP"
        self.user.profile.save()
        self.assertContains(self.client.get(f"/juego/{self.game.slug}/"), "£")


class SignupTests(TestCase):
    def test_signup_saves_profile_preferences(self):
        resp = self.client.post("/cuenta/registro/", {
            "first_name": "Nico", "last_name": "Prueba", "username": "nico", "email": "nico@example.com",
            "password1": "una-clave-larga-1", "password2": "una-clave-larga-1",
            "country": "ES", "currency": "USD", "email_alerts": "on", "accept_terms": "on",
        })
        self.assertEqual(resp.status_code, 302)
        user = get_user_model().objects.get(email="nico@example.com")
        self.assertEqual(user.profile.currency, "USD")
        self.assertEqual(user.first_name, "Nico")

    def test_signup_requires_terms(self):
        resp = self.client.post("/cuenta/registro/", {
            "username": "x", "email": "x@example.com", "password1": "una-clave-larga-1",
            "password2": "una-clave-larga-1", "country": "ES", "currency": "EUR",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(email="x@example.com").exists())
