from django.urls import reverse


def test_health_endpoint(client):
    url = reverse("health")
    response = client.get(url)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


