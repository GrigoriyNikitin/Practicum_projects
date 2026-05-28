from django_filters.rest_framework import FilterSet
from django_filters.rest_framework.filters import (BooleanFilter,
                                                   ModelMultipleChoiceFilter)
from recipes.models import Recipe, Tag
from rest_framework import filters


class IngredientFilter(filters.SearchFilter):
    """Кастомный фильтр для ингредиентов."""

    search_param = 'name'


class RecipeFilterSet(FilterSet):
    """Кастомный фильтр для рецептов.

    Реализована возможность фильтрации по:
    - избранному,
    - автору,
    - списку покупок
    - тегам.
    """

    tags = ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    is_favorited = BooleanFilter(method='get_is_favorited')
    is_in_shopping_cart = BooleanFilter(method='get_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ('tags', 'author', 'is_favorited', 'is_in_shopping_cart')

    def get_is_favorited(self, recipes, name, presence_in_favorites):
        return recipes.filter(
            favourites__user_id=self.request.user.pk
        ) if presence_in_favorites else recipes

    def get_is_in_shopping_cart(self, recipes, name, presence_in_shopcart):
        return recipes.filter(
            shopping_cart__user_id=self.request.user.pk
        ) if presence_in_shopcart else recipes
