from django.urls import path

from .views import ScanPipelineAPIView, ScanSegmentationAPIView, ScanSelectedAnalysisAPIView

urlpatterns = [
    path("", ScanPipelineAPIView.as_view(), name="scan-pipeline"),
    path("segment/", ScanSegmentationAPIView.as_view(), name="scan-segment"),
    path("selected/", ScanSelectedAnalysisAPIView.as_view(), name="scan-selected"),
]