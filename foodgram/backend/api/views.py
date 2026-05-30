from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from django_url_shortener.utils import shorten_url
from djoser.views import UserViewSet
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilterSet
from .pagination import PageLimitPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (AvatarSerializer, FavouritesSerializer,
                          FollowSerializer, IngredientSerializer,
                          ModifiedUserReadSerializer, RecipeWriteSerializer,
                          ShoppingCartSerializer, ShortLinkSerializer,
                          TagSerializer, UserFollowSerializer)

User = get_user_model()


class IsAuthenticatedOrReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """Общий ViewSet для определения разрешений к моделям Ingredient и Tag."""

    permission_classes = (IsAuthenticatedOrReadOnly,)


class IngredientViewSet(IsAuthenticatedOrReadOnlyViewSet):
    """ViewSet для управления ингредиентами."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (IngredientFilter,)
    search_fields = ('^name',)


class TagViewSet(IsAuthenticatedOrReadOnlyViewSet):
    """ViewSet для управления тегами рецептов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class RecipeUserMixin:
    """Миксин для добавления общего метода для рецептов и пользователей."""

    def _get_validated_serializer(self, request, data):
        """Общий метод для создания и валидации сериализатора."""
        self.get_object()
        serializer = self.get_serializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        return serializer


class RecipeViewSet(viewsets.ModelViewSet, RecipeUserMixin):
    """ViewSet для управления рецептами."""

    queryset = Recipe.objects.all()
    http_method_names = ('get', 'post', 'patch', 'delete', 'head', 'options')
    pagination_class = PageLimitPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilterSet

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        if self.action == 'get_link':
            return ShortLinkSerializer
        if self.action in {'shopping_cart', 'delete_shopping_cart'}:
            return ShoppingCartSerializer
        if self.action in {'favorite', 'delete_favorite'}:
            return FavouritesSerializer
        return RecipeWriteSerializer

    def get_permissions(self):
        if self.action in {'update', 'partial_update', 'destroy'}:
            return (IsAuthorOrReadOnly(),)
        elif self.action in {'create', 'favorite', 'delete_favorite',
                             'shopping_cart', 'delete_shopping_cart',
                             'download_shopping_cart'}:
            return (IsAuthenticated(),)
        return (AllowAny(),)

    @action(
        detail=True,
        url_path='get-link',
    )
    def get_link(self, request, pk):
        """Метод для получения коротких ссылок рецепта."""
        long_url = request.build_absolute_uri(
        ).replace('api/', '').removesuffix('get-link/')
        created, short_url = shorten_url(long_url)
        return Response({'short-link': short_url})

    @action(
        methods=('post',),
        detail=True,
    )
    def shopping_cart(self, request, pk):
        """Метод для добавления рецепта в список покупок."""
        data = {'user': request.user.id, 'recipe': pk}
        serializer = self._get_validated_serializer(request, data)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk):
        """Метод для удаления рецепта из списка покупок."""
        data = {'user': request.user.id, 'recipe': pk}
        self._get_validated_serializer(request, data)
        request.user.shopping_cart.filter(recipe_id=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=('post',),
        detail=True,
    )
    def favorite(self, request, pk):
        """Метод для добавления рецепта в избранное."""
        data = {'user': request.user.id, 'recipe': pk}
        serializer = self._get_validated_serializer(request, data)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk):
        """Метод для удаления рецепта из избранного."""
        data = {'user': request.user.id, 'recipe': pk}
        self._get_validated_serializer(request, data)
        request.user.favourites.filter(recipe_id=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def ingredients_to_txt(ingredients, user):
        """Метод для объединения ингредиентов в список для выгрузки."""
        shopping_list = f'Список покупок пользователя {user.username}: \n'
        for ingredient in ingredients:
            shopping_list += (
                f'  ‣ {ingredient["ingredient__name"]} '
                f'({ingredient["ingredient__measurement_unit"]}) — '
                f'{ingredient["sum"]}\n'
            )
        return shopping_list

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
    )
    def download_shopping_cart(self, request):
        """Метод для скачивания списка покупок пользователя."""
        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).order_by(
            'ingredient__name'
        ).annotate(sum=Sum('amount'))
        shopping_list = self.ingredients_to_txt(ingredients, request.user)
        return HttpResponse(shopping_list, content_type='text/plain')


class ModifiedUserViewSet(UserViewSet, RecipeUserMixin):
    """Кастомный ViewSet для управления пользователями."""

    queryset = User.objects.all()
    serializer_class = ModifiedUserReadSerializer
    pagination_class = PageLimitPagination
    lookup_field = 'pk'

    def get_queryset(self):
        return User.objects.all()

    def get_serializer_class(self):
        if self.action in {'subscribe', 'delete_subscribe'}:
            return FollowSerializer
        if self.action == 'subscriptions':
            return UserFollowSerializer
        if self.action in {'avatar', 'delete_avatar'}:
            return AvatarSerializer
        return super().get_serializer_class()

    @action(
        methods=('post',),
        detail=True,
        permission_classes=(IsAuthenticated,),
    )
    def subscribe(self, request, pk):
        """Метод для создания подписок на пользователей."""
        data = {'user': request.user.id, 'author': pk}
        serializer = self._get_validated_serializer(request, data)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, pk):
        """Метод для удаления подписок на пользователей."""
        data = {'user': request.user.id, 'author': pk}
        self._get_validated_serializer(request, data)
        request.user.subscriptions.filter(author_id=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
    )
    def subscriptions(self, request):
        """Метод для получения подписок на пользователя."""
        subscriptions = User.objects.filter(followers__user=self.request.user)
        serializer = self.get_serializer(
            self.paginate_queryset(subscriptions),
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        methods=('put',),
        detail=False,
        url_path='me/avatar',
        permission_classes=(IsAuthenticated,),
    )
    def avatar(self, request):
        """Метод для добавления аватара пользователя."""
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.avatar = serializer.validated_data['avatar']
        user.save()
        return Response(self.get_serializer(user).data)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        """Метод для удаления аватара пользователя."""
        request.user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
    )
    def me(self, request):
        """Метод для получения профиля текущего пользователя."""
        user = request.user
        return Response(self.get_serializer(user).data)
