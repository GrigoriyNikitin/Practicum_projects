from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import (Favourites, Follow, Ingredient, Recipe, RecipeIngredient,
                     ShoppingCart, Tag)

User = get_user_model()


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    pass


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author')
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)
    readonly_fields = ('count_add_to_favorite', 'created',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'author', 'tags', 'text',
                       'cooking_time', 'image')
        }),
        ('Даты', {
            'fields': ('created',)
        }),
        ('Статистика', {
            'fields': ('count_add_to_favorite',)
        }),
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description='Количество добавлений рецепта в избранное')
    def count_add_to_favorite(self, recipe):
        return recipe.favourites.count()


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    pass


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    pass


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    pass


@admin.register(Favourites)
class FavouritesAdmin(admin.ModelAdmin):
    pass
