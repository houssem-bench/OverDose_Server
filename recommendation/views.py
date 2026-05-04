from typing import Optional, Dict, Any, List

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view

from scan.models import Scan

from .models import RecommendationBatch, RecommendationItem
from .serializers import (
	RecommendationReportRequestSerializer,
	RecommendationRequestSerializer,
	RecommendationResponseSerializer,
)

try:
	from .reco_axe3.agents.search_agent import ProductSearchAgent
	from .reco_axe3.utils.report_parser import ReportParser
	_HAS_SEARCH_AGENT = True
except ImportError:
	_HAS_SEARCH_AGENT = False
	ProductSearchAgent = None
	ReportParser = None

# Global instances
_parser: Optional['ReportParser'] = None
_search_agent: Optional['ProductSearchAgent'] = None


def _danger_score_from_level(level):
	level_key = str(level or "").strip().upper()
	return {
		"CRITICAL": 0.9,
		"HIGH": 0.7,
		"MODERATE": 0.4,
		"LOW": 0.2,
		"SAFE": 0.0,
	}.get(level_key, 0.0)


def _map_recommendation_override(recommendation):
	value = str(recommendation or "").strip().lower()
	if value == "avoid":
		return "SUBSTITUTE"
	if value == "critical":
		return "ELIMINATE"
	return None


def _build_report_product_payload(product, verdict_lookup, score_lookup):
	product_id = str(product.get("product_id", ""))
	product_verdict = verdict_lookup.get(product_id, {})
	score_info = score_lookup.get(product_id, {})
	ingredients = product.get("ingredients", {})
	chemicals = ingredients.get("chemicals_evaluated", [])
	safe_skipped = ingredients.get("safe_skipped", [])
	combination_risks = product.get("combination_risks", {})
	summary = product.get("summary", {})
	product_risk_level = product_verdict.get("risk_level") or score_info.get("verdict") or "UNKNOWN"

	chemical_verdicts = []
	for chemical in chemicals:
		verdict = chemical.get("verdict", {})
		body_effects = chemical.get("body_effects", {})
		chemical_verdicts.append(
			{
				"name": chemical.get("name"),
				"uid": chemical.get("uid"),
				"cas": chemical.get("cas"),
				"danger_level": verdict.get("danger_level") or "UNKNOWN",
				"danger_score": _danger_score_from_level(verdict.get("danger_level")),
				"justification": verdict.get("justification", []),
				"target_organs": body_effects.get("target_organs", []),
				"exposure_effects": body_effects.get("exposure_effects", {}),
				"hazard_codes": chemical.get("hazard", {}).get("h_codes", []),
				"chemical_class": chemical.get("identity", {}).get("chemical_classes", []),
			}
		)

	return {
		"product_id": product_id,
		"product_name": product.get("product_name"),
		"usage": product.get("usage"),
		"drivers": product.get("drivers", []),
		"danger_level": product_risk_level,
		"danger_score": _danger_score_from_level(product_risk_level),
		"exposure_routes": product.get("exposure_type", []),
		"chemical_verdicts": chemical_verdicts,
		"summary": {
			"total_ingredients": summary.get("total_ingredients", len(chemicals) + len(safe_skipped)),
			"chemicals_evaluated": summary.get("chemicals_evaluated", len(chemicals)),
			"critical_count": summary.get("critical", 0),
			"high_count": summary.get("high", 0),
			"moderate_count": summary.get("moderate", 0),
			"low_count": summary.get("low", 0),
			"safe_count": summary.get("safe", len(safe_skipped)),
			"organ_overlap_flags": summary.get("organ_overlap_flags", 0),
		},
		"combination_risks": {
			"has_organ_overlap": combination_risks.get("organ_overlap", {}).get("has_overlap", False),
			"has_cumulative_presence": combination_risks.get("cumulative_presence", {}).get("checked", False),
			"overlapping_organs": combination_risks.get("organ_overlap", {}).get("overlapping_organs"),
		},
		"recommendation_override": _map_recommendation_override(product_verdict.get("recommendation")),
	}


def build_report_recommendation_payload(report_data):
	products = report_data.get("products", [])
	product_verdicts = report_data.get("product_verdicts", [])
	scoring_analysis = report_data.get("scoring_analysis", {})

	verdict_lookup = {str(item.get("product_id")): item for item in product_verdicts}
	score_lookup = {str(item.get("product_id")): item for item in scoring_analysis.get("product_risk_results", [])}

	results_products = [
		_build_report_product_payload(product, verdict_lookup, score_lookup)
		for product in products
	]

	search_results = []
	for product in products:
		verdict = verdict_lookup.get(str(product.get("product_id")), {})
		search_results.append(
			{
				"product_id": product.get("product_id"),
				"product_name": product.get("product_name"),
				"product_type": product.get("usage", "cosmetics"),
				"result": {
					"triggered": False,
					"top_k": 0,
					"count": 0,
					"results": [],
					"errors": [
						"Search module not wired for report ingestion in this backend yet."
					],
				},
				"recommendation": verdict.get("recommendation"),
			}
		)

	return {
		"status": "ok",
		"report_id": report_data.get("report_id"),
		"results": {
			"report_id": report_data.get("report_id"),
			"analyzed_at": report_data.get("analyzed_at"),
			"agent_version": report_data.get("agent_version"),
			"products": results_products,
		},
		"search": {
			"triggered": False,
			"top_k": 0,
			"count": 0,
			"results": search_results,
			"errors": [],
		},
	}


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
		if "products" in request.data and "report_id" in request.data:
			serializer = RecommendationReportRequestSerializer(data=request.data)
			serializer.is_valid(raise_exception=True)
			return Response(build_report_recommendation_payload(serializer.validated_data), status=status.HTTP_200_OK)

		serializer = RecommendationRequestSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		data = serializer.validated_data
		payload = build_mock_recommendations(data["scan_id"], data["risks"])
		_persist_recommendations(data["scan_id"], payload["recommendations"])

		response_serializer = RecommendationResponseSerializer(data=payload)
		response_serializer.is_valid(raise_exception=True)
		return Response(response_serializer.data, status=status.HTTP_200_OK)


# Helper functions for search agent
def _get_parser() -> Optional['ReportParser']:
	"""Lazy-initialize report parser"""
	global _parser
	if _parser is None and _HAS_SEARCH_AGENT:
		try:
			_parser = ReportParser()
		except Exception as e:
			return None
	return _parser


def _get_search_agent() -> Optional['ProductSearchAgent']:
	"""Lazy-initialize search agent"""
	global _search_agent
	if _search_agent is None and _HAS_SEARCH_AGENT:
		try:
			_search_agent = ProductSearchAgent()
		except Exception as e:
			return None
	return _search_agent


class ResearchReportAPIView(APIView):
	"""Parse research report and trigger product search"""
	
	def post(self, request):
		if not _HAS_SEARCH_AGENT:
			return Response(
				{
					"status": "error",
					"message": "Search agent not available. Please ensure the local recommendation support package is installed.",
					"report_id": request.data.get("report_id"),
					"results": None,
					"search": {"triggered": False, "count": 0, "results": [], "errors": ["Search module unavailable"]},
				},
				status=status.HTTP_503_SERVICE_UNAVAILABLE,
			)
		
		try:
			report = request.data if isinstance(request.data, dict) else request.data.dict()
			parser = _get_parser()
			agent = _get_search_agent()
			
			if not parser:
				return Response(
					{
						"status": "error",
						"message": "Failed to initialize report parser",
						"report_id": report.get("report_id"),
						"results": None,
						"search": {"triggered": False, "count": 0, "results": [], "errors": ["Parser initialization failed"]},
					},
					status=status.HTTP_500_INTERNAL_SERVER_ERROR,
				)
			
			# Parse the report
			parsed = parser.parse_report(report)

			raw_top_k = report.get("search_top_k", 1)
			search_top_k = raw_top_k if isinstance(raw_top_k, int) else 1
			search_top_k = max(1, min(20, search_top_k))

			results_payload = {
				"report_id": parsed.get("report_id", report.get("report_id")),
				"analyzed_at": parsed.get("analyzed_at", report.get("analyzed_at")),
				"agent_version": parsed.get("agent_version", report.get("agent_version")),
				"products": parsed.get("products", []),
			}

			search_results = []
			search_errors = []
			
			# Trigger search for each product if agent available
			if agent:
				for product in results_payload.get("products", []):
					try:
						product_name = product.get("product_name")
						product_type = product.get("usage", "cosmetics")

						result = agent.search_product_alternatives(
							product_name=product_name,
							product_type=product_type,
							top_k=search_top_k,
						)
						search_results.append({
							"product_id": product["product_id"],
							"product_name": product_name,
							"product_type": product_type,
							"result": result,
						})
					except Exception as e:
						search_errors.append({
							"product_id": product["product_id"],
							"product_name": product.get("product_name"),
							"error": str(e),
						})
					# Small delay to avoid overwhelming services
					import time
					time.sleep(0.5)
			
			return Response(
				{
					"status": "ok",
					"report_id": results_payload.get("report_id"),
					"results": results_payload,
					"search": {
						"triggered": bool(agent),
						"top_k": search_top_k if agent else 0,
						"count": len(search_results),
						"results": search_results,
						"errors": search_errors,
					},
				},
				status=status.HTTP_200_OK,
			)
		except Exception as e:
			return Response(
				{
					"status": "error",
					"message": str(e),
					"report_id": request.data.get("report_id"),
					"results": None,
					"search": {"triggered": False, "count": 0, "results": [], "errors": [str(e)]},
				},
				status=status.HTTP_500_INTERNAL_SERVER_ERROR,
			)


class SearchAlternativesAPIView(APIView):
	"""Search for product alternatives"""
	
	def post(self, request):
		if not _HAS_SEARCH_AGENT:
			return Response(
				{
					"status": "error",
					"message": "Search agent not available",
					"results": [],
					"errors": ["Search module unavailable"],
				},
				status=status.HTTP_503_SERVICE_UNAVAILABLE,
			)
		
		try:
			agent = _get_search_agent()
			if not agent:
				return Response(
					{
						"status": "error",
						"message": "Failed to initialize search agent",
						"results": [],
						"errors": ["Agent initialization failed"],
					},
					status=status.HTTP_500_INTERNAL_SERVER_ERROR,
				)
			
			product_name = request.data.get("product_name")
			product_type = request.data.get("product_type", "cosmetics")
			top_k = request.data.get("top_k", 1)
			
			if not product_name:
				return Response(
					{
						"status": "error",
						"message": "product_name is required",
						"results": [],
						"errors": ["Missing product_name"],
					},
					status=status.HTTP_400_BAD_REQUEST,
				)
			
			result = agent.search_product_alternatives(
				product_name=product_name,
				product_type=product_type,
				top_k=top_k,
			)
			
			return Response(
				{
					"status": "ok",
					"product_name": product_name,
					"product_type": product_type,
					"top_k": top_k,
					"results": result,
					"errors": [],
				},
				status=status.HTTP_200_OK,
			)
		except Exception as e:
			return Response(
				{
					"status": "error",
					"message": str(e),
					"results": [],
					"errors": [str(e)],
				},
				status=status.HTTP_500_INTERNAL_SERVER_ERROR,
			)


class SearchAlternativesBatchAPIView(APIView):
	"""Batch search for multiple product alternatives"""
	
	def post(self, request):
		if not _HAS_SEARCH_AGENT:
			return Response(
				{
					"status": "error",
					"message": "Search agent not available",
					"results": [],
					"errors": ["Search module unavailable"],
				},
				status=status.HTTP_503_SERVICE_UNAVAILABLE,
			)
		
		try:
			agent = _get_search_agent()
			if not agent:
				return Response(
					{
						"status": "error",
						"message": "Failed to initialize search agent",
						"results": [],
						"errors": ["Agent initialization failed"],
					},
					status=status.HTTP_500_INTERNAL_SERVER_ERROR,
				)
			
			items = request.data.get("items", [])
			if not items:
				return Response(
					{
						"status": "error",
						"message": "items array is required",
						"results": [],
						"errors": ["Missing items array"],
					},
					status=status.HTTP_400_BAD_REQUEST,
				)
			
			search_results = []
			search_errors = []
			
			for item in items:
				try:
					product_name = item.get("product_name")
					if not product_name:
						search_errors.append({
							"product_name": "unknown",
							"error": "Missing product_name in item",
						})
						continue
					
					result = agent.search_product_alternatives(
						product_name=product_name,
						product_type=item.get("product_type", "cosmetics"),
						top_k=item.get("top_k", 5),
					)
					search_results.append({
						"product_name": product_name,
						"result": result,
					})
				except Exception as e:
					search_errors.append({
						"product_name": item.get("product_name", "unknown"),
						"error": str(e),
					})
				# Small delay between requests
				import time
				time.sleep(0.5)
			
			return Response(
				{
					"status": "ok",
					"count": len(search_results),
					"results": search_results,
					"errors": search_errors,
				},
				status=status.HTTP_200_OK,
			)
		except Exception as e:
			return Response(
				{
					"status": "error",
					"message": str(e),
					"results": [],
					"errors": [str(e)],
				},
				status=status.HTTP_500_INTERNAL_SERVER_ERROR,
			)
