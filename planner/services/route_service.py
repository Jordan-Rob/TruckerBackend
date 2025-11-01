import os
from typing import Any, Dict, List, Tuple

import requests
import polyline


class RouteServiceError(Exception):
    pass


class NotRoutableError(RouteServiceError):
    """Raised when ORS cannot find a routable point near provided coordinates.

    Typically happens when points are off-road or not truck-legal (using HGV profile).
    """
    pass


class RouteService:
    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.api_key = os.getenv("ORS_API_KEY", "")
        # Ask ORS to return GeoJSON via query param to avoid unsupported body params
        self.base_url = "https://api.openrouteservice.org/v2/directions/driving-hgv?format=geojson"

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise RouteServiceError("ORS_API_KEY not configured")
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

    def get_route(
        self,
        coordinates: List[Tuple[float, float]],
    ) -> Dict[str, Any]:
        payload = {
            "coordinates": [[lon, lat] for lat, lon in coordinates],
            # we don't need verbose turn-by-turn instructions right now
            "instructions": False,
        }
        response = self.session.post(self.base_url, json=payload, headers=self._headers(), timeout=30)
        if response.status_code >= 400:
            # Try to extract structured error from ORS
            try:
                err = response.json()
                code = err.get("error", {}).get("code")
                message = err.get("error", {}).get("message", "")
            except Exception:
                code = None
                message = response.text

            not_routable_signals = (
                code in {2010, 2011, 2020} or
                "Could not find routable point" in message or
                "not routable" in message.lower()
            )
            if not_routable_signals:
                raise NotRoutableError(message or "No routable truck-legal roads near provided coordinates")
            raise RouteServiceError(f"OpenRouteService error: {response.status_code} {message}")
        data = response.json()
        # Two shapes are observed from ORS depending on headers/options:
        # 1) GeoJSON FeatureCollection with features[0]
        # 2) JSON with routes[] that contains geometry and summary
        try:
            if isinstance(data, dict) and "features" in data and data["features"]:
                feature = data["features"][0]
                geometry = feature["geometry"]
                summary = feature["properties"]["summary"]
                segments = feature["properties"].get("segments", [])
            elif isinstance(data, dict) and "routes" in data and data["routes"]:
                route0 = data["routes"][0]
                geometry = route0["geometry"]  # could be geojson or encoded polyline
                summary = route0["summary"]
                segments = route0.get("segments", [])
            else:
                raise KeyError("unrecognized shape")
        except (KeyError, IndexError, TypeError) as exc:
            # If ORS returned an object without expected keys, convert to a clearer error
            raise RouteServiceError("Unexpected response format from OpenRouteService") from exc

        # Decode polyline if we got a string instead of GeoJSON
        if isinstance(geometry, str):
            try:
                # Decode polyline (returns list of [lat, lon] tuples)
                decoded = polyline.decode(geometry)
                # Convert to GeoJSON LineString format with [lon, lat] coordinates
                geometry = {
                    "type": "LineString",
                    "coordinates": [[lon, lat] for lat, lon in decoded]
                }
            except Exception as e:
                raise RouteServiceError(f"Failed to decode polyline geometry: {e}") from e
        # Ensure geometry is in proper GeoJSON format
        elif isinstance(geometry, dict) and geometry.get("type") != "LineString":
            # If it's a dict but not LineString, try to normalize
            if "coordinates" in geometry:
                geometry = {
                    "type": "LineString",
                    "coordinates": geometry["coordinates"]
                }
            else:
                raise RouteServiceError("Geometry is not in expected format")

        return {
            "distance_m": summary.get("distance", 0),
            "duration_s": summary.get("duration", 0),
            "geometry": geometry,
            "segments": segments,
        }

    @staticmethod
    def plan_stops(distance_m: float, duration_s: float) -> Dict[str, Any]:
        """
        Plan stops based on assumptions:
        - Fueling at least once every 1,000 miles
        - Property-carrying driver: 11h drive/day max, 14h duty window
        """
        miles = distance_m / 1609.34
        hours = duration_s / 3600
        # Assumption: Fueling at least once every 1,000 miles
        fueling_stops = int(miles // 1000)
        # Property-carrying driver: 11h drive/day max (70hr/8day cycle enforced in ELD service)
        driving_hours_per_day = 11
        days = int((hours + driving_hours_per_day - 1) // driving_hours_per_day)
        breaks = int(hours // 8)
        return {
            "fueling_stops": fueling_stops,
            "estimated_days": max(1, days),
            "required_breaks": breaks,
        }



