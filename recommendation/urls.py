from django.urls import path

from .views import (
	RecommendationAPIView,
	ResearchReportAPIView,
	SearchAlternativesAPIView,
	SearchAlternativesBatchAPIView,
)

urlpatterns = [
    path("", RecommendationAPIView.as_view(), name="recommendation-evaluate"),
    path("research/report", ResearchReportAPIView.as_view(), name="research-report"),
    path("research/parse", ResearchReportAPIView.as_view(), name="research-parse"),
    path("search/alternatives", SearchAlternativesAPIView.as_view(), name="search-alternatives"),
    path("search/alternatives/batch", SearchAlternativesBatchAPIView.as_view(), name="search-alternatives-batch"),
]