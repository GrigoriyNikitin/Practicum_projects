from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .constants import (AMOUNT_MAX_VALUE, AMOUNT_MIN_VALUE,
                        COOKING_TIME_MAX_VALUE, COOKING_TIME_MIN_VALUE,
                        MAX_LENGTH, NAME_MAX_LENGTH)

User = get_user_model()


class Tag(models.Model):
    """Модель для тегов."""

    name = models.CharField(
        max_length=MAX_LENGTH,
        unique=True,
        verbose_name='Название тега'
    )
    slug = models.SlugField(
        max_length=MAX_LENGTH,
        unique=True,
        verbose_name='Идентификатор тега',
        help_text='Разрешены символы латиницы, цифры, дефис и подчёркивание.'
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'slug'),
                name='unique_tag'
            ),
        )
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель для ингредиентов."""

    name = models.CharField(
        max_length=NAME_MAX_LENGTH,
        db_index=True,
        verbose_name='Название ингредиента'
    )
    measurement_unit = models.CharField(
        max_length=MAX_LENGTH,
        verbose_name='Единица измерения'
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель для рецептов."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор рецепта',
    )
    name = models.CharField(
        max_length=NAME_MAX_LENGTH,
        verbose_name='Название рецепта'
    )
    image = models.ImageField(
        upload_to='recipes/',
        verbose_name='Изображение рецепта'
    )
    text = models.TextField(verbose_name='Описание рецепта')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты',
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги'
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления в минутах',
        validators=(
            MinValueValidator(COOKING_TIME_MIN_VALUE),
            MaxValueValidator(COOKING_TIME_MAX_VALUE)
        ),
    )
    created = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата публикации рецепта'
    )

    class Meta:
        ordering = ('-created',)
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепт'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    """Промежуточная модель.

    Для управления отношениями «многие ко многим»
    между моделями Recipe и Ingredient.
    """

    recipe = models.ForeignKey(
        Recipe,
        related_name='ingredients_in_recipe',
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        related_name='recipes_with_ingredients',
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество ингредиента в рецепте',
        validators=(
            MinValueValidator(AMOUNT_MIN_VALUE),
            MaxValueValidator(AMOUNT_MAX_VALUE)
        ),
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_ingredient_in_recipe'
            ),
        )
        ordering = ('recipe',)
        verbose_name = 'рецепт-ингредиент'
        verbose_name_plural = 'Рецепты-ингредиенты'

    def __str__(self):
        return f'{self.recipe} - {self.ingredient}'


class Follow(models.Model):
    """Модель для подписок на авторов рецептов."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name='Автор рецепта'
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'author'),
                name='unique_follow'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='prevent_self_follow'
            ),
        )
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'{self.user} {self.author}'


class FavouritesShoppingCart(models.Model):
    """Модель, от которой наследуются модели избранного и списка покупок."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.user} {self.recipe}'


class Favourites(FavouritesShoppingCart):
    """Модель для списка избранных рецептов."""

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_favourites'
            ),
        )
        default_related_name = 'favourites'
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранное'


class ShoppingCart(FavouritesShoppingCart):
    """Модель для списка покупок."""

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_shoppingcart'
            ),
        )
        default_related_name = 'shopping_cart'
        verbose_name = 'cписок покупок'
        verbose_name_plural = 'Списки покупок'
