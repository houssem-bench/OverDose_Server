from django.db import models

from scan.models import Scan


class RecommendationBatch(models.Model):
	scan = models.OneToOneField(Scan, on_delete=models.CASCADE, related_name="recommendation_batch")
	payload = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"RecommendationBatch for scan {self.scan_id}"


class RecommendationItem(models.Model):
	batch = models.ForeignKey(RecommendationBatch, on_delete=models.CASCADE, related_name="items")
	product = models.CharField(max_length=255)
	reason = models.TextField()

	class Meta:
		ordering = ["product"]

	def __str__(self):
		return self.product
