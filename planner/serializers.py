from rest_framework import serializers


class LocationSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class PlanTripRequestSerializer(serializers.Serializer):
    current_location = LocationSerializer()
    pickup_location = LocationSerializer()
    dropoff_location = LocationSerializer()
    current_cycle_hours_used = serializers.FloatField(min_value=0)


class PlanTripResponseSerializer(serializers.Serializer):
    distance_m = serializers.FloatField()
    duration_s = serializers.FloatField()
    geometry = serializers.JSONField()
    segments = serializers.JSONField()
    stops = serializers.DictField()


