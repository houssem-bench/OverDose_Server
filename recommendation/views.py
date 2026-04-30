from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from scan.models import Scan

from .models import RecommendationBatch, RecommendationItem
from .serializers import RecommendationRequestSerializer, RecommendationResponseSerializer


def build_mock_recommendations(scan_id, risks):
	recommendations = []
	for item in risks:
		ingredient = item.get("ingredient", "unknown")
		level = item.get("level", "low")
		recommendations.append(
			{
				"product": f"Alternative for {ingredient}",
				"reason": f"Mock recommendation generated for {level} risk ingredient.",
			}
		)

	if not recommendations:
		recommendations.append(
			{
				"product": "Generic Safe Option",
				"reason": "No risks found, default placeholder recommendation.",
			}
		)

	return {"scan_id": scan_id, "recommendations": recommendations}


def _persist_recommendations(scan_id, recommendations):
	scan = Scan.objects.filter(id=scan_id).first()
	if not scan:
		return

	batch, _ = RecommendationBatch.objects.get_or_create(scan=scan)
	batch.payload = {"scan_id": scan_id, "recommendations": recommendations}
	batch.save(update_fields=["payload", "updated_at"])
	batch.items.all().delete()
	RecommendationItem.objects.bulk_create(
		[
			RecommendationItem(
				batch=batch,
				product=item["product"],
				reason=item["reason"],
			)
			for item in recommendations
		]
	)


class RecommendationAPIView(APIView):
	def post(self, request):
		serializer = RecommendationRequestSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		data = serializer.validated_data
		payload = build_mock_recommendations(data["scan_id"], data["risks"])
		_persist_recommendations(data["scan_id"], payload["recommendations"])

		response_serializer = RecommendationResponseSerializer(data=payload)
		response_serializer.is_valid(raise_exception=True)
		return Response(response_serializer.data, status=status.HTTP_200_OK)
