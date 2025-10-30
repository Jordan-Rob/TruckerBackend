from django.urls import path
from .views import HealthCheckView, PlanTripView


urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("plan_trip/", PlanTripView.as_view(), name="plan-trip"),
]


