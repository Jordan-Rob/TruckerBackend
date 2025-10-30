from django.urls import reverse
import pytest


@pytest.mark.django_db
def test_plan_trip_with_save_creates_trip(client, monkeypatch):
    # mock ORS
    from unittest.mock import patch, Mock

    monkeypatch.setenv("ORS_API_KEY", "test-key")
    with patch("planner.services.route_service.requests.Session") as mock_session:
        session_instance = Mock()
        mock_session.return_value = session_instance
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "features": [
                {
                    "geometry": {"type": "LineString", "coordinates": [[-73.0, 40.0], [-74.0, 41.0]]},
                    "properties": {
                        "summary": {"distance": 2000.0, "duration": 1200.0},
                        "segments": [{"distance": 2000.0, "duration": 1200.0, "steps": []}],
                    },
                }
            ]
        }
        session_instance.post.return_value = response

        payload = {
            "current_location": {"lat": 40.0, "lon": -73.0},
            "pickup_location": {"lat": 40.5, "lon": -73.5},
            "dropoff_location": {"lat": 41.0, "lon": -74.0},
            "current_cycle_hours_used": 5.0,
        }

        url = reverse("plan-trip") + "?save=1"
        res = client.post(url, data=payload, content_type="application/json")
        assert res.status_code == 200
        data = res.json()
        assert "trip" in data
        assert data["trip"]["planned_distance_m"] == 2000.0


