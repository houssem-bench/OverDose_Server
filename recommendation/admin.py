from django.contrib import admin

from .models import RecommendationBatch, RecommendationItem


@admin.register(RecommendationBatch)
class RecommendationBatchAdmin(admin.ModelAdmin):
	list_display = ("id", "scan", "created_at", "updated_at")
	autocomplete_fields = ("scan",)


@admin.register(RecommendationItem)
class RecommendationItemAdmin(admin.ModelAdmin):
	list_display = ("id", "batch", "product")
	search_fields = ("product",)
