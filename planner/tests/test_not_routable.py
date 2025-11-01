from unittest.mock import patch, Mock
from django.urls import reverse
import pytest


@pytest.mark.django_db
def test_plan_trip_not_routable_returns_422(client, monkeypatch):
    monkeypatch.setenv("ORS_API_KEY", "test-key")
    with patch("planner.services.route_service.requests.Session") as mock_session:
        session_instance = Mock()
        mock_session.return_value = session_instance
        response = Mock()
        response.status_code = 404
        response.json.return_value = {
            "error": {"code": 2010, "message": "Could not find routable point within a radius of 350.0 meters"}
        }
        session_instance.post.return_value = response

        url = reverse("plan-trip")
        payload = {
            "current_location": {"lat": 40.0, "lon": -73.0},
            "pickup_location": {"lat": 40.5, "lon": -73.5},
            "dropoff_location": {"lat": 41.0, "lon": -74.0},
            "current_cycle_hours_used": 5.0,
        }
        res = client.post(url, data=payload, content_type="application/json")
        assert res.status_code == 422
        data = res.json()
        assert "No truck-legal roads" in data["detail"]

