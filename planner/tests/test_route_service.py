import os
from unittest.mock import Mock

import pytest

from planner.services.route_service import RouteService, RouteServiceError


def test_plan_stops_calculation():
    stats = RouteService.plan_stops(distance_m=1609.34 * 2100, duration_s=3600 * 30)
    assert stats["fueling_stops"] >= 2
    assert stats["estimated_days"] >= 3
    assert stats["required_breaks"] >= 3


def test_get_route_success(monkeypatch):
    monkeypatch.setenv("ORS_API_KEY", "test-key")
    session = Mock()
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "features": [
            {
                "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
                "properties": {
                    "summary": {"distance": 1000.0, "duration": 600.0},
                    "segments": [{"distance": 1000.0, "duration": 600.0, "steps": []}],
                },
            }
        ]
    }
    session.post.return_value = response

    svc = RouteService(session=session)
    data = svc.get_route(coordinates=[(40.0, -73.0), (41.0, -74.0)])
    assert data["distance_m"] == 1000.0
    assert data["duration_s"] == 600.0
    assert data["geometry"]["type"] == "LineString"


def test_get_route_requires_api_key(monkeypatch):
    monkeypatch.delenv("ORS_API_KEY", raising=False)
    svc = RouteService()
    with pytest.raises(RouteServiceError):
        svc.get_route(coordinates=[(40.0, -73.0), (41.0, -74.0)])


