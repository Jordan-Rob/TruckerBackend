from rest_framework import serializers
from .models import Trip, Stop, ELDLog


class LocationSerializer(serializers.Serializer):
    """Geographic coordinates (latitude and longitude)."""
    lat = serializers.FloatField(
        help_text="Latitude coordinate (-90 to 90)"
    )
    lon = serializers.FloatField(
        help_text="Longitude coordinate (-180 to 180)"
    )


class PlanTripRequestSerializer(serializers.Serializer):
    """
    Request payload for trip planning.
    
    Provides route calculation between current location, pickup, and dropoff points,
    with HOS (Hours of Service) compliance and ELD log generation.
    """
    current_location = LocationSerializer(
        help_text="Driver's current location coordinates"
    )
    pickup_location = LocationSerializer(
        help_text="Pickup location coordinates (adds 1 hour to trip duration)"
    )
    dropoff_location = LocationSerializer(
        help_text="Dropoff location coordinates (adds 1 hour to trip duration)"
    )
    current_cycle_hours_used = serializers.FloatField(
        min_value=0,
        help_text="Hours already used in the current 70-hour/8-day cycle (property-carrying driver rule)"
    )


class TripSerializer(serializers.ModelSerializer):
    """Trip model serializer with location, distance, duration, and route geometry."""
    
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
        read_only_fields = ("id", "created_at")


class StopsSerializer(serializers.Serializer):
    """Planned stops information."""
    fueling_stops = serializers.IntegerField(
        help_text="Number of fueling stops required (at least once every 1,000 miles)"
    )
    estimated_days = serializers.IntegerField(
        help_text="Estimated number of days needed for the trip"
    )
    required_breaks = serializers.IntegerField(
        help_text="Required breaks based on HOS rules"
    )


class ELDSegmentSerializer(serializers.Serializer):
    """ELD log segment representing a period of duty status."""
    start = serializers.FloatField(
        help_text="Start hour (0-24, hours since midnight)"
    )
    end = serializers.FloatField(
        help_text="End hour (0-24, hours since midnight)"
    )
    status = serializers.IntegerField(
        help_text="Duty status: 1=Off Duty, 2=Sleeper Berth, 3=Driving, 4=On Duty (not driving)"
    )


class ELDDaySerializer(serializers.Serializer):
    """Daily ELD log with segments."""
    segments = serializers.ListField(
        child=ELDSegmentSerializer(),
        help_text="List of duty status segments for the day"
    )
    note = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Optional note (e.g., '34-hour reset required')"
    )


class ELDLogsResponseSerializer(serializers.Serializer):
    """Response containing daily ELD logs."""
    days = serializers.ListField(
        child=ELDDaySerializer(),
        help_text="Array of daily ELD logs"
    )


class PlanTripResponseSerializer(serializers.Serializer):
    """
    Response from trip planning endpoint.
    
    Includes route information, planned stops, and optionally the saved trip object.
    """
    distance_m = serializers.FloatField(
        help_text="Total distance in meters"
    )
    duration_s = serializers.FloatField(
        help_text="Total duration in seconds (includes 2 hours for pickup and dropoff)"
    )
    geometry = serializers.JSONField(
        help_text="Route geometry as GeoJSON (LineString or MultiLineString)"
    )
    segments = serializers.JSONField(
        required=False,
        help_text="Route segments information"
    )
    stops = StopsSerializer(
        help_text="Planned stops (fueling, breaks, estimated days)"
    )
    trip = TripSerializer(
        required=False,
        help_text="Saved trip object (only present if ?save=1 query parameter was used)"
    )

