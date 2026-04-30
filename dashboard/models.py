from django.db import models


class DashboardNote(models.Model):
	title = models.CharField(max_length=255)
	payload = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return self.title
