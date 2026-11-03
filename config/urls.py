from django.contrib import admin
from django.urls import include, path

from accounts import views as account_views

urlpatterns = [
    path("admin/", admin.site.urls),
    # Acceso y registro en una sola pantalla (antes que las rutas de allauth para sustituirlas)
    path("cuenta/entrar/", account_views.AccessLoginView.as_view(), name="account_login"),
    path("cuenta/registro/", account_views.AccessSignupView.as_view(), name="account_signup"),
    # Las rutas por defecto de allauth comparten nombre con las nuestras; las apuntamos a la misma
    # pantalla para que ningún enlace acabe en las plantillas sin estilos de la librería.
    path("cuenta/login/", account_views.AccessLoginView.as_view()),
    path("cuenta/signup/", account_views.AccessSignupView.as_view()),
    path("cuenta/", include("allauth.urls")),
    path("cuenta/perfil/", account_views.profile, name="profile"),
    path("alertas/", include("alerts.urls")),
    path("", include("catalog.urls")),
    path("", include("core.urls")),
]

handler404 = "core.views.not_found"
