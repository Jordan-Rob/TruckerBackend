from django.urls import reverse
import pytest


def test_eld_logs_from_duration(client):
    url = reverse("eld-logs") + "?duration_s=39600"  # 11h
    res = client.get(url)
    assert res.status_code == 200
    data = res.json()
    assert "days" in data and len(data["days"]) == 1


@pytest.mark.django_db
def test_eld_logs_from_trip(client, monkeypatch):
    # Create a trip quickly via save=1 on plan_trip
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
                        "summary": {"distance": 1000.0, "duration": 600.0},
                        "segments": [{"distance": 1000.0, "duration": 600.0, "steps": []}],
                    },
                }
            ]
        }
        session_instance.post.return_value = response

        plan_url = reverse("plan-trip") + "?save=1"
        payload = {
            "current_location": {"lat": 40.0, "lon": -73.0},
            "pickup_location": {"lat": 40.5, "lon": -73.5},
            "dropoff_location": {"lat": 41.0, "lon": -74.0},
            "current_cycle_hours_used": 5.0,
        }
        plan_res = client.post(plan_url, data=payload, content_type="application/json")
        assert plan_res.status_code == 200
        trip_id = plan_res.json()["trip"]["id"]

    url = reverse("eld-logs") + f"?trip_id={trip_id}"
    res = client.get(url)
    assert res.status_code == 200
    data = res.json()
    assert "days" in data and len(data["days"]) >= 1


