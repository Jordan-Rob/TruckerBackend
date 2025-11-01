from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .serializers import (
    PlanTripRequestSerializer,
    PlanTripResponseSerializer,
    TripSerializer,
    ELDDaySerializer,
    ELDLogsResponseSerializer,
)
from .services.route_service import RouteService, RouteServiceError, NotRoutableError
from .models import Trip
from .services.eld_service import generate_eld_logs


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Health check",
        description="Check if the API is running and healthy.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "ok"}
                }
            }
        },
        tags=["Health"]
    )
    def get(self, request):
        return Response({"status": "ok"})


class PlanTripView(APIView):
    @extend_schema(
        summary="Plan a trip",
        description="""
        Plan a truck route between current location, pickup, and dropoff points.
        
        **Features:**
        - Calculates route using OpenRouteService
        - Plans fueling stops (at least once every 1,000 miles)
        - Estimates trip duration including 1 hour for pickup and 1 hour for dropoff
        - Respects HOS rules for property-carrying drivers (70hrs/8days)
        
        **Query Parameters:**
        - `save=1` or `save=true`: Persist the trip in the database (returns trip object in response)
        
        **Assumptions:**
        - Property-carrying driver, 70hrs/8days cycle
        - No adverse driving conditions
        - Fueling at least once every 1,000 miles
        - 1 hour for pickup and drop-off
        """,
        request=PlanTripRequestSerializer,
        responses={
            200: PlanTripResponseSerializer,
            400: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"},
                    "field_name": {"type": "array", "items": {"type": "string"}}
                }
            },
            422: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"},
                    "hint": {"type": "string"},
                    "reason": {"type": "string"}
                }
            },
            502: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"}
                }
            },
            503: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"}
                }
            }
        },
        examples=[
            OpenApiExample(
                "Example Request",
                value={
                    "current_location": {"lat": 40.7128, "lon": -74.0060},
                    "pickup_location": {"lat": 39.9526, "lon": -75.1652},
                    "dropoff_location": {"lat": 41.8781, "lon": -87.6298},
                    "current_cycle_hours_used": 10.0
                },
                request_only=True
            ),
            OpenApiExample(
                "Example Response",
                value={
                    "distance_m": 160934.4,
                    "duration_s": 36000.0,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-74.0060, 40.7128], [-75.1652, 39.9526]]
                    },
                    "segments": [],
                    "stops": {
                        "fueling_stops": 0,
                        "estimated_days": 1,
                        "required_breaks": 1
                    },
                    "trip": {
                        "id": 1,
                        "created_at": "2024-01-15T10:00:00Z",
                        "current_lat": 40.7128,
                        "current_lon": -74.0060,
                        "pickup_lat": 39.9526,
                        "pickup_lon": -75.1652,
                        "dropoff_lat": 41.8781,
                        "dropoff_lon": -87.6298,
                        "current_cycle_hours_used": 10.0,
                        "planned_distance_m": 160934.4,
                        "planned_duration_s": 36000.0,
                        "geometry": {"type": "LineString", "coordinates": []}
                    }
                },
                response_only=True
            )
        ],
        tags=["Trip Planning"],
        parameters=[
            OpenApiParameter(
                name="save",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="If true, persist the trip in the database (returns trip object in response)",
                required=False,
                examples=[
                    OpenApiExample("Save trip", value=True),
                    OpenApiExample("Don't save", value=False),
                ]
            ),
        ]
    )
    def post(self, request):
        serializer = PlanTripRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        def normalize_lat_lon(lat: float, lon: float) -> tuple[float, float]:
            """Return a best-effort (lat, lon) pair.
            - If values look swapped (abs(lat) > 90 and abs(lon) <= 90), swap them.
            - Otherwise return as-is.
            """
            if abs(lat) > 90 and abs(lon) <= 90:
                return lon, lat
            return lat, lon

        coordinates = [
            normalize_lat_lon(payload["current_location"]["lat"], payload["current_location"]["lon"]),
            normalize_lat_lon(payload["pickup_location"]["lat"], payload["pickup_location"]["lon"]),
            normalize_lat_lon(payload["dropoff_location"]["lat"], payload["dropoff_location"]["lon"]),
        ]

        route_service = RouteService()
        try:
            route = route_service.get_route(coordinates)
        except NotRoutableError as exc:
            return Response(
                {
                    "detail": "No truck-legal roads found near one or more points.",
                    "hint": "Move the marker closer to a public road or adjust to a nearby address. Some roads restrict HGV access.",
                    "reason": str(exc),
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except RouteServiceError as exc:
            error_msg = str(exc)
            if "ORS_API_KEY" in error_msg:
                return Response(
                    {"detail": "OpenRouteService API key not configured. Please set ORS_API_KEY in backend/.env"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            return Response({"detail": f"Route service error: {error_msg}"}, status=status.HTTP_502_BAD_GATEWAY)

        # Add 1h for pickup and 1h for dropoff to overall time context (not geometry)
        adjusted_duration_s = route["duration_s"] + 2 * 3600
        stops = route_service.plan_stops(route["distance_m"], adjusted_duration_s)

        output = {
            "distance_m": route["distance_m"],
            "duration_s": adjusted_duration_s,
            "geometry": route["geometry"],
            "segments": route["segments"],
            "stops": stops,
        }

        # Optionally persist if requested
        if request.query_params.get("save") in {"1", "true", "True"}:
            trip = Trip.objects.create(
                current_lat=payload["current_location"]["lat"],
                current_lon=payload["current_location"]["lon"],
                pickup_lat=payload["pickup_location"]["lat"],
                pickup_lon=payload["pickup_location"]["lon"],
                dropoff_lat=payload["dropoff_location"]["lat"],
                dropoff_lon=payload["dropoff_location"]["lon"],
                current_cycle_hours_used=payload["current_cycle_hours_used"],
                planned_distance_m=route["distance_m"],
                planned_duration_s=adjusted_duration_s,
                geometry=route["geometry"],
            )
            output["trip"] = TripSerializer(trip).data

        # Return the structured output directly to preserve read-only fields like trip.id
        return Response(output)


class ELDLogsView(APIView):
    @extend_schema(
        summary="Generate ELD logs",
        description="""
        Generate daily ELD (Electronic Logging Device) logs for a trip.
        
        **Query Parameters (one required):**
        - `trip_id`: ID of a saved trip (automatically uses trip's duration and cycle hours)
        - `duration_s`: Trip duration in seconds (for trips not saved in database)
        - `current_cycle_hours_used`: Optional, hours used in 70-hour/8-day cycle (only used with duration_s)
        
        **Response:**
        Returns an array of daily logs, each containing:
        - `segments`: Array of duty status segments (start hour, end hour, status code)
        - `note`: Optional note for special cases (e.g., 34-hour reset required)
        
        **Status Codes:**
        - 1: Off Duty
        - 2: Sleeper Berth
        - 3: Driving
        - 4: On Duty (not driving)
        
        **HOS Rules Enforced:**
        - Property-carrying driver: 70 hours maximum within any rolling 8-day period
        - Up to 11 hours driving per day
        - 14-hour duty window per day
        - 34-hour reset required after reaching 70-hour limit
        """,
        parameters=[
            OpenApiParameter(
                name="trip_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="ID of a saved trip",
                required=False
            ),
            OpenApiParameter(
                name="duration_s",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description="Trip duration in seconds (if trip not saved)",
                required=False
            ),
            OpenApiParameter(
                name="current_cycle_hours_used",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description="Hours already used in current 70-hour cycle (only used with duration_s)",
                required=False
            ),
        ],
        responses={
            200: ELDLogsResponseSerializer,
            400: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"}
                }
            },
            404: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"}
                }
            }
        },
        examples=[
            OpenApiExample(
                "Example Response",
                value={
                    "days": [
                        {
                            "segments": [
                                {"start": 0.0, "end": 0.5, "status": 4},
                                {"start": 0.5, "end": 8.5, "status": 3},
                                {"start": 8.5, "end": 9.0, "status": 1},
                                {"start": 9.0, "end": 11.0, "status": 3},
                                {"start": 11.0, "end": 11.5, "status": 4},
                                {"start": 11.5, "end": 24.0, "status": 1}
                            ]
                        }
                    ]
                },
                response_only=True
            )
        ],
        tags=["ELD Logs"]
    )
    def get(self, request):
        trip_id = request.query_params.get("trip_id")
        duration_s = request.query_params.get("duration_s")
        if not trip_id and not duration_s:
            return Response({"detail": "Provide trip_id or duration_s"}, status=status.HTTP_400_BAD_REQUEST)

        current_cycle_hours = 0.0
        if trip_id:
            try:
                trip = Trip.objects.get(id=trip_id)
            except Trip.DoesNotExist:
                return Response({"detail": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)
            total_s = float(trip.planned_duration_s)
            current_cycle_hours = float(trip.current_cycle_hours_used)
        else:
            try:
                total_s = float(duration_s)
                # Allow optional current_cycle_hours_used via query param
                cycle_param = request.query_params.get("current_cycle_hours_used")
                if cycle_param:
                    current_cycle_hours = float(cycle_param)
            except (TypeError, ValueError) as e:
                return Response({"detail": f"Invalid parameter: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        logs = generate_eld_logs(total_s, current_cycle_hours_used=current_cycle_hours)
        return Response({"days": logs})
