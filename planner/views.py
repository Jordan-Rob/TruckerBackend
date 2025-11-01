from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .serializers import PlanTripRequestSerializer, PlanTripResponseSerializer, TripSerializer
from .services.route_service import RouteService, RouteServiceError, NotRoutableError
from .models import Trip
from .services.eld_service import generate_eld_logs


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"})


class PlanTripView(APIView):
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
    def get(self, request):
        """
        Generate logs from either a trip id or a provided duration_s.
        - Query: trip_id=<id> OR duration_s=<seconds>
        - Uses current_cycle_hours_used from trip or query param for 70hr/8day cycle enforcement
        """
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
