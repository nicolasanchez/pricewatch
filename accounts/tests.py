from django.test import TestCase
from django.urls import reverse


class AccessPagesTests(TestCase):
    def test_login_and_signup_links_use_styled_page(self):
        # Los botones usan estos nombres; deben llevar siempre a la pantalla propia, no a la de allauth.
        for name in ("account_login", "account_signup"):
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, "account/access.html")

    def test_allauth_default_urls_use_styled_page(self):
        for url in ("/cuenta/login/", "/cuenta/signup/", "/cuenta/entrar/", "/cuenta/registro/"):
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, "account/access.html")

    def test_access_page_has_minimal_header(self):
        resp = self.client.get(reverse("account_login"))
        self.assertTemplateUsed(resp, "partials/header_minimal.html")
        self.assertTemplateNotUsed(resp, "partials/header.html")
