from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "brand", "category", "extraction_method", "created_at")
	list_filter = ("category", "extraction_method")
	search_fields = ("name", "brand", "barcode")
