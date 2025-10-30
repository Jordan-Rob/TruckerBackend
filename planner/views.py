from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .serializers import PlanTripRequestSerializer, PlanTripResponseSerializer
from .services.route_service import RouteService, RouteServiceError


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

        coordinates = [
            (payload["current_location"]["lat"], payload["current_location"]["lon"]),
            (payload["pickup_location"]["lat"], payload["pickup_location"]["lon"]),
            (payload["dropoff_location"]["lat"], payload["dropoff_location"]["lon"]),
        ]

        route_service = RouteService()
        try:
            route = route_service.get_route(coordinates)
        except RouteServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

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

        response_serializer = PlanTripResponseSerializer(data=output)
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.data)
