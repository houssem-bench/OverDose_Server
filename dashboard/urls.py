from django.urls import path

from .views import DashboardRecommendationPreviewAPIView, DashboardSummaryAPIView, DashboardView

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard-home"),
    path("api/dashboard/summary/", DashboardSummaryAPIView.as_view(), name="dashboard-summary"),
    path("api/dashboard/recommendation/", DashboardRecommendationPreviewAPIView.as_view(), name="dashboard-recommendation-preview"),
]