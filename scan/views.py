import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from scan.legacy.runtime import analyze_ingredients_from_image, analyze_selected_products, segment_image

from recommendation.views import build_mock_recommendations
from risk.views import build_mock_risks

from .serializers import (
	AnalysisBatchResponseSerializer,
	AnalyzeSelectedRequestSerializer,
	ScanPipelineResponseSerializer,
	ScanSerializer,
	SegmentationRequestSerializer,
	SegmentationResponseSerializer,
)


logger = logging.getLogger(__name__)


class ScanPipelineAPIView(APIView):
	def post(self, request):
		if "image" not in request.FILES:
			return Response({"detail": "image is required."}, status=status.HTTP_400_BAD_REQUEST)

		serializer = ScanSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		scan = serializer.save()

		image_path = scan.image.path if scan.image else None
		image_url = scan.image.url if scan.image else None
		ingredients: list[str] = []

		if image_path:
			try:
				ingredients = analyze_ingredients_from_image(
					scan_id=scan.id,
					image_path=image_path,
					image_url=image_url,
				)
			except Exception:
				logger.exception("Real scan pipeline failed for scan_id=%s", scan.id)
				ingredients = []

		risk_result = build_mock_risks(scan.id, ingredients)
		recommendation_result = build_mock_recommendations(scan.id, risk_result["risks"])

		payload = {
			"scan_id": scan.id,
			"ingredients": ingredients,
			"risks": risk_result["risks"],
			"recommendations": recommendation_result["recommendations"],
		}
		response_serializer = ScanPipelineResponseSerializer(data=payload)
		response_serializer.is_valid(raise_exception=True)
		return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ScanSegmentationAPIView(APIView):
	def post(self, request):
		image = request.FILES.get("image")
		if image is None:
			return Response({"detail": "image is required."}, status=status.HTTP_400_BAD_REQUEST)

		content_type = getattr(image, "content_type", "") or ""
		if not content_type.startswith("image/"):
			return Response({"detail": "File must be an image"}, status=status.HTTP_400_BAD_REQUEST)

		input_serializer = SegmentationRequestSerializer(data=request.data)
		input_serializer.is_valid(raise_exception=True)
		data = input_serializer.validated_data
		mode = str(data.get("segmentation_mode", "auto")).strip().lower()
		expected_products = data.get("expected_products")

		try:
			session_id, products = segment_image(
				image_bytes=image.read(),
				filename=getattr(image, "name", "upload.jpg"),
				segmentation_mode=mode,
				expected_products=expected_products,
			)
		except ValueError as exc:
			return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

		payload = {
			"session_id": session_id,
			"segmentation_mode": mode,
			"expected_products": expected_products,
			"total_products": len(products),
			"products": products,
		}
		output_serializer = SegmentationResponseSerializer(data=payload)
		output_serializer.is_valid(raise_exception=True)
		return Response(output_serializer.data, status=status.HTTP_200_OK)


class ScanSelectedAnalysisAPIView(APIView):
	def post(self, request):
		serializer = AnalyzeSelectedRequestSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		data = serializer.validated_data

		session_id = data["session_id"]
		product_ids = data["product_ids"]

		try:
			results = analyze_selected_products(session_id=session_id, product_ids=product_ids)
		except LookupError:
			return Response({"detail": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
		except ValueError as exc:
			return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

		payload = {
			"session_id": session_id,
			"analyzed_count": len(results),
			"results": results,
		}
		output_serializer = AnalysisBatchResponseSerializer(data=payload)
		output_serializer.is_valid(raise_exception=True)
		return Response(output_serializer.data, status=status.HTTP_200_OK)
