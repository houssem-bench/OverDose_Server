from django.db import models

from scan.models import Scan


class RiskAssessment(models.Model):
	scan = models.OneToOneField(Scan, on_delete=models.CASCADE, related_name="risk_assessment")
	payload = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"RiskAssessment for scan {self.scan_id}"


class RiskItem(models.Model):
	LEVEL_LOW = "low"
	LEVEL_MEDIUM = "medium"
	LEVEL_HIGH = "high"
	LEVEL_CHOICES = [
		(LEVEL_LOW, "Low"),
		(LEVEL_MEDIUM, "Medium"),
		(LEVEL_HIGH, "High"),
	]

	assessment = models.ForeignKey(RiskAssessment, on_delete=models.CASCADE, related_name="items")
	ingredient = models.CharField(max_length=255)
	level = models.CharField(max_length=32, choices=LEVEL_CHOICES)

	class Meta:
		ordering = ["ingredient"]

	def __str__(self):
		return f"{self.ingredient} ({self.level})"
