from django.contrib import admin

from .models import Notification, PriceAlert


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ("user", "game", "store", "target_price", "currency", "is_paused", "triggered_at", "deleted_at")
    list_filter = ("is_paused", "currency", "channel")
    search_fields = ("user__email", "game__title")
    autocomplete_fields = ("game",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "created_at", "read_at")
    search_fields = ("user__email", "message")
