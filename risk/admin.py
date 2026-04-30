from django.contrib import admin

from .models import RiskAssessment, RiskItem


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
	list_display = ("id", "scan", "created_at", "updated_at")
	autocomplete_fields = ("scan",)


@admin.register(RiskItem)
class RiskItemAdmin(admin.ModelAdmin):
	list_display = ("id", "assessment", "ingredient", "level")
	list_filter = ("level",)
