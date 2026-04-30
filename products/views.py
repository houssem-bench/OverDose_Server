from rest_framework import generics
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Product
from .serializers import ProductSerializer


class ProductListCreateAPIView(generics.ListCreateAPIView):
	queryset = Product.objects.select_related("owner").all()
	serializer_class = ProductSerializer
	permission_classes = [IsAuthenticatedOrReadOnly]

	def get_queryset(self):
		queryset = super().get_queryset()
		user = self.request.user
		if user.is_authenticated:
			return queryset.filter(owner=user) | queryset.filter(owner__isnull=True)
		return queryset

	def perform_create(self, serializer):
		owner = self.request.user if self.request.user.is_authenticated else None
		serializer.save(owner=owner)
