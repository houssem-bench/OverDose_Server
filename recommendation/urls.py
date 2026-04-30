from django.urls import path

from .views import RecommendationAPIView

urlpatterns = [
    path("", RecommendationAPIView.as_view(), name="recommendation-evaluate"),
]