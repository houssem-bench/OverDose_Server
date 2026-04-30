from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from scan.models import Scan

from .models import RiskAssessment, RiskItem
from .serializers import RiskRequestSerializer, RiskResponseSerializer


def build_mock_risks(scan_id, ingredients):
	levels = ["low", "medium", "high"]
	risks = [
		{
			"ingredient": ingredient,
			"level": levels[index % len(levels)],
		}
		for index, ingredient in enumerate(ingredients)
	]
	return {"scan_id": scan_id, "risks": risks}


def _persist_risks(scan_id, risks):
	scan = Scan.objects.filter(id=scan_id).first()
	if not scan:
		return

	assessment, _ = RiskAssessment.objects.get_or_create(scan=scan)
	assessment.payload = {"scan_id": scan_id, "risks": risks}
	assessment.save(update_fields=["payload", "updated_at"])
	assessment.items.all().delete()
	RiskItem.objects.bulk_create(
		[
			RiskItem(
				assessment=assessment,
				ingredient=item["ingredient"],
				level=item["level"],
			)
			for item in risks
		]
	)


class RiskEvaluationAPIView(APIView):
	def post(self, request):
		serializer = RiskRequestSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		data = serializer.validated_data
		payload = build_mock_risks(data["scan_id"], data["ingredients"])
		_persist_risks(data["scan_id"], payload["risks"])

		response_serializer = RiskResponseSerializer(data=payload)
		response_serializer.is_valid(raise_exception=True)
		return Response(response_serializer.data, status=status.HTTP_200_OK)
