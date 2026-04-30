from django.urls import path

from .views import DashboardSummaryAPIView, DashboardView

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard-home"),
    path("api/dashboard/summary/", DashboardSummaryAPIView.as_view(), name="dashboard-summary"),
]