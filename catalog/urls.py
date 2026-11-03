from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("juegos/", views.games, name="games"),
    path("juego/<slug:slug>/", views.game_detail, name="game"),
]
