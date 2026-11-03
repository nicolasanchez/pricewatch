from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "currency", "country", "email_alerts", "alert_frequency")
    list_filter = ("currency", "country", "alert_frequency")
    search_fields = ("user__email", "user__username")
    filter_horizontal = ("favorite_stores",)
