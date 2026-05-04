from django.urls import path

from .views import (
	AllergyListCreateAPIView,
	CurrentUserAPIView,
	CurrentUserAllergiesAPIView,
	LoginAPIView,
	RegisterAPIView,
	UserAllergyListCreateAPIView,
	UserListCreateAPIView,
)

urlpatterns = [
    path("", UserListCreateAPIView.as_view(), name="user-list-create"),
    path("auth/register/", RegisterAPIView.as_view(), name="auth-register"),
    path("auth/login/", LoginAPIView.as_view(), name="auth-login"),
    path("me/", CurrentUserAPIView.as_view(), name="current-user"),
	path("me/allergies/", CurrentUserAllergiesAPIView.as_view(), name="current-user-allergies"),
    path("allergies/", AllergyListCreateAPIView.as_view(), name="allergy-list-create"),
    path("user-allergies/", UserAllergyListCreateAPIView.as_view(), name="user-allergy-list-create"),
]