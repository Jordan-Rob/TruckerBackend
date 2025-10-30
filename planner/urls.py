from django.urls import path
from .views import HealthCheckView, PlanTripView, ELDLogsView


urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("plan_trip/", PlanTripView.as_view(), name="plan-trip"),
    path("eld_logs/", ELDLogsView.as_view(), name="eld-logs"),
]


