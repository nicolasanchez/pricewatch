from django.contrib import admin

from .models import Deal, ExchangeRate, Game, PriceSnapshot, Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "cheapshark_id", "is_official", "is_active")
    list_editable = ("is_official", "is_active")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


class DealInline(admin.TabularInline):
    model = Deal
    extra = 0
    fields = ("store", "price", "normal_price", "currency", "savings", "deal_rating", "drm", "last_change")


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("title", "genre", "metacritic_score", "steam_rating_percent", "is_aaa", "popularity")
    list_filter = ("is_aaa", "steam_deck_verified", "genre")
    search_fields = ("title", "developer")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [DealInline]


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ("game", "store", "price", "normal_price", "currency", "savings", "updated_at")
    list_filter = ("store",)
    search_fields = ("game__title",)
    autocomplete_fields = ("game",)


@admin.register(PriceSnapshot)
class PriceSnapshotAdmin(admin.ModelAdmin):
    list_display = ("game", "store", "price", "currency", "recorded_at")
    list_filter = ("store",)
    search_fields = ("game__title",)
    date_hierarchy = "recorded_at"


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("currency", "rate", "date")
    list_filter = ("currency",)
