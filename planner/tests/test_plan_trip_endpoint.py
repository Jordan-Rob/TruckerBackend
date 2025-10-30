from unittest.mock import patch, Mock
from django.urls import reverse


def _payload():
    return {
        "current_location": {"lat": 40.0, "lon": -73.0},
        "pickup_location": {"lat": 40.5, "lon": -73.5},
        "dropoff_location": {"lat": 41.0, "lon": -74.0},
        "current_cycle_hours_used": 10.0,
    }


@patch("planner.services.route_service.requests.Session")
def test_plan_trip_success(mock_session, client, settings, monkeypatch):
    monkeypatch.setenv("ORS_API_KEY", "test-key")
    session_instance = Mock()
    mock_session.return_value = session_instance
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "features": [
            {
                "geometry": {"type": "LineString", "coordinates": [[-73.0, 40.0], [-74.0, 41.0]]},
                "properties": {
                    "summary": {"distance": 1000.0, "duration": 600.0},
                    "segments": [{"distance": 1000.0, "duration": 600.0, "steps": []}],
                },
            }
        ]
    }
    session_instance.post.return_value = response

    url = reverse("plan-trip")
    res = client.post(url, data=_payload(), content_type="application/json")
    assert res.status_code == 200
    data = res.json()
    assert data["distance_m"] == 1000.0
    assert data["duration_s"] == 600.0 + 7200  # includes pickup/dropoff time
    assert data["geometry"]["type"] == "LineString"
    assert "stops" in data


def test_plan_trip_missing_fields(client):
    url = reverse("plan-trip")
    res = client.post(url, data={}, content_type="application/json")
    assert res.status_code == 400



