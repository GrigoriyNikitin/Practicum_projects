from django.contrib.auth import get_user_model
from rest_framework import permissions

User = get_user_model()


class IsAuthorOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    """Кастомное разрешение: только для автора или только на чтение."""

    def has_object_permission(self, request, view, recipe):
        return (
            request.method in permissions.SAFE_METHODS
            or recipe.author == request.user
        )
