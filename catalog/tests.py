from decimal import Decimal
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from catalog.categories import games_for, get_category
from catalog.currency import clear_rates_cache, convert, format_money, parse_amount
from catalog.models import Deal, ExchangeRate, Game, PriceSnapshot, Store
from catalog.services import import_deals, sync_rates


class CurrencyTests(TestCase):
    def setUp(self):
        ExchangeRate.objects.create(currency="USD", rate=Decimal("1.08"), date="2026-11-01")
        ExchangeRate.objects.create(currency="GBP", rate=Decimal("0.84"), date="2026-11-01")
        clear_rates_cache()

    def test_convert_usd_to_eur_and_gbp(self):
        self.assertEqual(convert(Decimal("10.80"), "USD", "EUR"), Decimal("10.00"))
        self.assertEqual(convert(Decimal("10.80"), "USD", "GBP"), Decimal("8.40"))
        self.assertEqual(convert(Decimal("5"), "EUR", "EUR"), Decimal("5.00"))

    def test_missing_rate_returns_original(self):
        self.assertEqual(convert(Decimal("7"), "USD", "JPY"), Decimal("7.00"))

    def test_format_and_parse(self):
        self.assertEqual(format_money(Decimal("1234.5"), "EUR"), "1.234,50 €")
        self.assertEqual(parse_amount("24,99 €"), Decimal("24.99"))
        self.assertEqual(parse_amount("1.024,50"), Decimal("1024.50"))
        self.assertEqual(parse_amount("24.99"), Decimal("24.99"))
        self.assertIsNone(parse_amount("abc"))
        self.assertIsNone(parse_amount("-3"))


class DemoDataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", user="demo@example.com", stdout=mock.MagicMock())

    def setUp(self):
        clear_rates_cache()

    def test_categories_filter_and_sort(self):
        cheap = list(games_for(get_category("menos-5")))
        self.assertTrue(cheap)
        self.assertTrue(all(g.best_price <= convert(5, "EUR", "USD") for g in cheap))
        meta = list(games_for(get_category("metacritic")))
        self.assertTrue(all(g.metacritic_score >= 90 for g in meta))
        scores = [g.metacritic_score for g in meta]
        self.assertEqual(scores, sorted(scores, reverse=True))
        steam = Store.objects.get(name="Steam")
        self.assertTrue(all(g.deals.filter(store=steam).exists() for g in games_for(get_category("todas"), steam)))

    def test_pages_render(self):
        for url in ["/", "/juegos/", "/juegos/?categoria=descuento", "/juego/hades-ii/", "/legal/", "/buscar/?q=hades"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_search_returns_matches(self):
        resp = self.client.get("/buscar/?q=hades")
        self.assertContains(resp, "Hades II")
        self.assertNotContains(resp, "Balatro")

    def test_prices_shown_in_euros_by_default(self):
        resp = self.client.get("/juego/hades-ii/")
        self.assertContains(resp, "23,99 €")


class ImportTests(TestCase):
    def test_import_deals_creates_snapshot_only_when_price_changes(self):
        Store.objects.create(cheapshark_id=1, name="Steam")
        row = {"storeID": "1", "gameID": "77", "title": "Juego X", "dealID": "abc", "salePrice": "9.99",
               "normalPrice": "19.99", "savings": "50.02", "dealRating": "8.5", "isOnSale": "1",
               "metacriticScore": "88", "steamRatingPercent": "93", "steamAppID": "123", "lastChange": "1760000000",
               "releaseDate": "1600000000", "thumb": ""}
        self.assertEqual(import_deals([row]), 1)
        self.assertEqual(import_deals([row]), 0)
        row["salePrice"] = "7.99"
        self.assertEqual(import_deals([row]), 1)
        game = Game.objects.get(cheapshark_game_id=77)
        self.assertEqual(PriceSnapshot.objects.filter(game=game).count(), 2)
        self.assertEqual(Deal.objects.get(game=game).price, Decimal("7.99"))
        self.assertEqual(game.metacritic_score, 88)

    @mock.patch("catalog.services._get")
    def test_sync_rates(self, fake_get):
        fake_get.return_value = {"base": "EUR", "date": "2026-11-02", "rates": {"USD": 1.1, "GBP": 0.85}}
        saved, day = sync_rates()
        self.assertEqual(saved, 2)
        self.assertEqual(convert(Decimal("11"), "USD", "EUR"), Decimal("10.00"))
