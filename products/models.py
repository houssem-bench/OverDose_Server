from django.conf import settings
from django.db import models


class Product(models.Model):
	CATEGORY_FOOD = "food"
	CATEGORY_COSMETIC = "cosmetic"
	CATEGORY_CHOICES = [
		(CATEGORY_FOOD, "Food"),
		(CATEGORY_COSMETIC, "Cosmetic"),
	]

	EXTRACTION_LENS = "lens"
	EXTRACTION_BARCODE = "barcode"
	EXTRACTION_CHOICES = [
		(EXTRACTION_LENS, "Lens"),
		(EXTRACTION_BARCODE, "Barcode"),
	]

	name = models.CharField(max_length=255)
	brand = models.CharField(max_length=255)
	owner = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		related_name="products",
		null=True,
		blank=True,
	)
	category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
	ingredients = models.JSONField(default=list, blank=True)
	barcode = models.CharField(max_length=64, blank=True)
	extraction_method = models.CharField(max_length=32, choices=EXTRACTION_CHOICES)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.brand} - {self.name}"
