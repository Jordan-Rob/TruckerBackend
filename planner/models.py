from django.db import models


class Trip(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    current_lat = models.FloatField()
    current_lon = models.FloatField()
    pickup_lat = models.FloatField()
    pickup_lon = models.FloatField()
    dropoff_lat = models.FloatField()
    dropoff_lon = models.FloatField()

    current_cycle_hours_used = models.FloatField(default=0)

    planned_distance_m = models.FloatField(default=0)
    planned_duration_s = models.FloatField(default=0)

    geometry = models.JSONField(default=dict)

    def __str__(self) -> str:  # pragma: no cover
        return f"Trip #{self.pk}"


class Stop(models.Model):
    TYPE_CHOICES = (
        ("fuel", "Fuel"),
        ("break", "Break"),
        ("rest", "Rest"),
    )

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="stops")
    sequence_index = models.PositiveIntegerField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    at_distance_m = models.FloatField(default=0)
    at_time_s = models.FloatField(default=0)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["sequence_index"]


class ELDLog(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="eld_logs")
    day_index = models.PositiveIntegerField()
    generated_at = models.DateTimeField(auto_now_add=True)
    sheet = models.JSONField(default=dict)

    class Meta:
        unique_together = ("trip", "day_index")

# Create your models here.
