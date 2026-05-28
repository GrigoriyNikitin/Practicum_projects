from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (IngredientViewSet, ModifiedUserViewSet, RecipeViewSet,
                    TagViewSet)

app_name = 'api'

router_v1 = DefaultRouter()
router_v1.register('ingredients', IngredientViewSet)
router_v1.register('tags', TagViewSet)
router_v1.register('recipes', RecipeViewSet)
router_v1.register('users', ModifiedUserViewSet)

urlpatterns = [
    path('', include(router_v1.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
