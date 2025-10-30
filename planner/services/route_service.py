import os
from typing import Any, Dict, List, Tuple

import requests


class RouteServiceError(Exception):
    pass


class RouteService:
    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.api_key = os.getenv("ORS_API_KEY", "")
        self.base_url = "https://api.openrouteservice.org/v2/directions/driving-hgv"

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise RouteServiceError("ORS_API_KEY not configured")
        return {"Authorization": self.api_key, "Content-Type": "application/json"}

    def get_route(
        self,
        coordinates: List[Tuple[float, float]],
    ) -> Dict[str, Any]:
        payload = {"coordinates": [[lon, lat] for lat, lon in coordinates]}
        response = self.session.post(self.base_url, json=payload, headers=self._headers(), timeout=30)
        if response.status_code >= 400:
            raise RouteServiceError(f"OpenRouteService error: {response.status_code} {response.text}")
        data = response.json()
        try:
            feature = data["features"][0]
            geometry = feature["geometry"]
            summary = feature["properties"]["summary"]
            segments = feature["properties"]["segments"]
        except (KeyError, IndexError) as exc:
            raise RouteServiceError("Unexpected response format from OpenRouteService") from exc

        return {
            "distance_m": summary.get("distance", 0),
            "duration_s": summary.get("duration", 0),
            "geometry": geometry,
            "segments": segments,
        }

    @staticmethod
    def plan_stops(distance_m: float, duration_s: float) -> Dict[str, Any]:
        miles = distance_m / 1609.34
        hours = duration_s / 3600
        fueling_stops = int(miles // 1000)
        # Very simplified HOS model: 11h drive/day, 10h off-duty rest, 30m break per 8h
        driving_hours_per_day = 11
        days = int((hours + driving_hours_per_day - 1) // driving_hours_per_day)
        breaks = int(hours // 8)
        return {
            "fueling_stops": fueling_stops,
            "estimated_days": max(1, days),
            "required_breaks": breaks,
        }



