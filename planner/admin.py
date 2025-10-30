from django.contrib import admin
from .models import Trip, Stop, ELDLog


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "planned_distance_m",
        "planned_duration_s",
    )
    search_fields = ("id",)


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ("id", "trip", "sequence_index", "type")
    list_filter = ("type",)


@admin.register(ELDLog)
class ELDLogAdmin(admin.ModelAdmin):
    list_display = ("id", "trip", "day_index", "generated_at")

# Register your models here.
