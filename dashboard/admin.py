from django.contrib import admin

from .models import DashboardNote


@admin.register(DashboardNote)
class DashboardNoteAdmin(admin.ModelAdmin):
	list_display = ("id", "title", "created_at")
	search_fields = ("title",)
