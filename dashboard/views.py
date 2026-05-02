import json

from django.views.generic import TemplateView
from rest_framework.response import Response
from rest_framework.views import APIView

from scan.models import Scan
from recommendation.models import RecommendationBatch
from users.models import User

from .serializers import DashboardSummarySerializer


class DashboardView(TemplateView):
	template_name = "dashboard/index.html"

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		users = User.objects.all()[:10]
		scans = Scan.objects.select_related("user").all()[:10]

		sample_result = {
			"scan_id": scans[0].id if scans else None,
			"ingredients": ["ingredient_1", "ingredient_2"],
			"risks": [{"ingredient": "ingredient_1", "level": "medium"}],
			"recommendations": [
				{
					"product": "Alternative for ingredient_1",
					"reason": "Mock recommendation generated for medium risk ingredient.",
				}
			],
		}

		recommendation_request = {
			"scan_id": scans[0].id if scans else None,
			"risks": [{"ingredient": "ingredient_1", "level": "medium"}],
		}

		context["users"] = users
		context["scans"] = scans
		context["sample_result_json"] = json.dumps(sample_result, indent=2)
		context["recommendation_scan_id"] = recommendation_request["scan_id"] or ""
		context["recommendation_request_json"] = json.dumps(recommendation_request, indent=2)
		return context


class DashboardSummaryAPIView(APIView):
	def get(self, request):
		payload = {
			"total_users": User.objects.count(),
			"total_scans": Scan.objects.count(),
			"sample_result": {
				"scan_id": 1,
				"ingredients": ["ingredient_1", "ingredient_2"],
				"risks": [{"ingredient": "ingredient_1", "level": "low"}],
				"recommendations": [
					{
						"product": "Alternative for ingredient_1",
						"reason": "Mock recommendation generated for low risk ingredient.",
					}
				],
			},
		}
		serializer = DashboardSummarySerializer(data=payload)
		serializer.is_valid(raise_exception=True)
		return Response(serializer.data)


class DashboardRecommendationPreviewAPIView(APIView):
	def get(self, request):
		scan_id = request.query_params.get("scan_id")
		if not scan_id:
			return Response({"detail": "scan_id is required."}, status=400)

		try:
			scan_id_int = int(scan_id)
		except (TypeError, ValueError):
			return Response({"detail": "scan_id must be an integer."}, status=400)

		batch = (
			RecommendationBatch.objects.select_related("scan")
			.prefetch_related("items")
			.filter(scan_id=scan_id_int)
			.first()
		)
		if not batch:
			return Response({"detail": "Recommendation batch not found."}, status=404)

		payload = {
			"scan_id": batch.scan_id,
			"payload": batch.payload,
			"item_count": batch.items.count(),
			"items": [
				{
					"product": item.product,
					"reason": item.reason,
				}
				for item in batch.items.all()
			],
		}
		return Response(payload)
