from rest_framework import serializers
from .models import Trip, Stop, ELDLog


class LocationSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class PlanTripRequestSerializer(serializers.Serializer):
    current_location = LocationSerializer()
    pickup_location = LocationSerializer()
    dropoff_location = LocationSerializer()
    current_cycle_hours_used = serializers.FloatField(min_value=0)


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = (
            "id",
            "created_at",
            "current_lat",
            "current_lon",
            "pickup_lat",
            "pickup_lon",
            "dropoff_lat",
            "dropoff_lon",
            "current_cycle_hours_used",
            "planned_distance_m",
            "planned_duration_s",
            "geometry",
        )


class PlanTripResponseSerializer(serializers.Serializer):
    distance_m = serializers.FloatField()
    duration_s = serializers.FloatField()
    geometry = serializers.JSONField()
    segments = serializers.JSONField()
    stops = serializers.DictField()
    trip = TripSerializer(required=False)



