from django.urls import path

from .views import RiskEvaluationAPIView

urlpatterns = [
    path("", RiskEvaluationAPIView.as_view(), name="risk-evaluate"),
]