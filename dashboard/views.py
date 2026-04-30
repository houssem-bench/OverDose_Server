import json

from django.views.generic import TemplateView
from rest_framework.response import Response
from rest_framework.views import APIView

from scan.models import Scan
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

		context["users"] = users
		context["scans"] = scans
		context["sample_result_json"] = json.dumps(sample_result, indent=2)
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
