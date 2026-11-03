from django.urls import path

from . import views

app_name = "alerts"

urlpatterns = [
    path("", views.alert_list, name="list"),
    path("crear/<slug:slug>/", views.create, name="create"),
    path("<int:pk>/fila/", views.row, name="row"),
    path("<int:pk>/editar/", views.edit, name="edit"),
    path("<int:pk>/objetivo/", views.save_target, name="save_target"),
    path("<int:pk>/pausar/", views.toggle_pause, name="pause"),
    path("<int:pk>/eliminar/", views.delete, name="delete"),
    path("<int:pk>/deshacer/", views.undo, name="undo"),
    path("avisos/leidos/", views.mark_read, name="mark_read"),
]
