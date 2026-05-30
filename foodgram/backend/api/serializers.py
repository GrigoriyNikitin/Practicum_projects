import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django_url_shortener.models import ShortUrl
from djoser.serializers import UserCreateSerializer
from recipes.models import (Favourites, Follow, Ingredient, Recipe,
                            RecipeIngredient, ShoppingCart, Tag)
from rest_framework import serializers

User = get_user_model()


class ModifiedUserReadSerializer(UserCreateSerializer):
    """Сериализатор для чтения экземпляров пользователей."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, user_instance):
        user = self.context.get('request').user
        if user.is_authenticated and user != user_instance:
            return user.subscriptions.filter(author=user_instance).exists()
        return False


class ModifiedUserWriteSerializer(ModifiedUserReadSerializer):
    """Сериализатор для создания экземпляров пользователей."""

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'password')
        extra_kwargs = {'password': {'write_only': True}}


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов рецептов."""

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""

    class Meta:
        model = Ingredient
        fields = '__all__'


class Base64ImageField(serializers.ImageField):
    """Кастомный тип поля для декодирования картинки в формате base64."""

    def to_internal_value(self, data):
        if not (isinstance(data, str) and data.startswith('data:image')):
            return super().to_internal_value(data)
        format, imgstr = data.split(';base64,')
        ext = format.split('/')[-1]
        data = ContentFile(
            base64.b64decode(imgstr), name=f'foodgram.{ext}'
        )
        return super().to_internal_value(data)


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления/удаления аватара пользователя."""

    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения промежуточной модели РецептыИнгридиенты."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""

    tags = TagSerializer(many=True)
    author = ModifiedUserReadSerializer()
    ingredients = RecipeIngredientReadSerializer(
        source='ingredients_in_recipe',
        many=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart', 'name',
                  'image', 'text', 'cooking_time')
        read_only_fields = ('author',)

    def get_is_favorited(self, obj):
        """Метод для проверки нахождения рецепта в списке избранного."""
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Favourites.objects.filter(
            user=request.user, recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        """Метод для проверки нахождения рецепта в списке покупок."""
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(
            user=request.user, recipe=obj
        ).exists()


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для записи промежуточной модели РецептыИнгридиенты."""

    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')

    def validate_id(self, value):
        if not Ingredient.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                'Указанного ингредиента еще нет, '
                'обратитесь к администратору!'
            )
        return value

    def validate_amount(self, value):
        if value < 1:
            raise serializers.ValidationError(
                'Убедитесь, что значение количества '
                'ингредиента больше единицы!'
            )
        return value


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""

    ingredients = RecipeIngredientWriteSerializer(
        many=True,
        allow_empty=False,
    )
    image = Base64ImageField()
    # Задаём параметр allow_empty=False для тегов:
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        allow_empty=False,
    )

    class Meta:
        model = Recipe
        fields = (
            'name', 'tags', 'ingredients', 'cooking_time',
            'author', 'image', 'text'
        )
        read_only_fields = ('author',)

    def to_representation(self, instance):
        """Метод представления модели."""
        return RecipeReadSerializer(
            instance,
            context={'request': self.context.get('request')}
        ).data

    def validate(self, attrs):
        tags = attrs.get('tags')
        ingredients = attrs.get('ingredients')
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Поле отсутствует'}
            )
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Поле отсуствует'}
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                'Теги рецепта не должны повторяться!'
            )
        ingr_pk_list = [item.get('id') for item in ingredients]
        if len(ingr_pk_list) != len(set(ingr_pk_list)):
            raise serializers.ValidationError(
                'Ингредиенты в рецепте не должны повторяться!'
            )
        return attrs

    def create_ingredients(self, ingredients, recipe):
        """Метод создания ингредиентов в рецепте."""
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                # При вводе ингредиента с несуществующим первичным ключом
                # возникнет исключение с соответсвующим сообщением
                # в соответствии с логикой вышеописанного (строка 144)
                # метода validate_id():
                ingredient=Ingredient.objects.get(pk=item.get('id')),
                amount=item.get('amount'),
            )
            for item in ingredients
        )

    def create_tags(self, tags, recipe):
        """Метод добавления тегов для рецепта."""
        recipe.tags.set(tags)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        self.create_ingredients(ingredients, recipe)
        self.create_tags(tags, recipe)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        self.create_tags(tags, instance)
        ingredients = validated_data.pop('ingredients')
        instance.ingredients.clear()
        self.create_ingredients(ingredients, instance)
        instance = super().update(instance, validated_data)
        return instance


class RecipeShortSerializer(serializers.ModelSerializer):
    """Сериализатор для рецептов в списке покупок/избранном."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок."""

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate(self, shop_cart):
        user = shop_cart.get('user')
        request = self.context['request']
        exists = user.shopping_cart.filter(
            recipe=shop_cart.get('recipe')
        ).exists()
        if request.method == 'POST' and exists:
            raise serializers.ValidationError(
                'Рецепт уже находится в списке покупок!'
            )
        if request.method == 'DELETE' and not exists:
            raise serializers.ValidationError(
                'Указанного рецепта нет в списке покупок!'
            )
        return shop_cart

    def to_representation(self, instance):
        """Метод представления модели."""
        return RecipeShortSerializer(
            instance.recipe,
            context={'request': self.context.get('request')}
        ).data


class FavouritesSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного."""

    class Meta:
        model = Favourites
        fields = ('user', 'recipe')

    def validate(self, favourite):
        user = favourite.get('user')
        request = self.context['request']
        exists = user.favourites.filter(
            recipe=favourite.get('recipe')
        ).exists()
        if request.method == 'POST' and exists:
            raise serializers.ValidationError(
                'Рецепт уже находится в избранном!'
            )
        if request.method == 'DELETE' and not exists:
            raise serializers.ValidationError(
                'Указанного рецепта нет в избранном!'
            )
        return favourite

    def to_representation(self, instance):
        """Метод представления модели."""
        return RecipeShortSerializer(
            instance.recipe,
            context={'request': self.context.get('request')}
        ).data


class UserFollowSerializer(ModifiedUserReadSerializer):
    """Сериализатор для подписок."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count',
        read_only=True
    )

    class Meta:
        model = User
        fields = ModifiedUserReadSerializer.Meta.fields + ('recipes',
                                                           'recipes_count')

    def validate(self, data):
        if data['user'] == data['author']:
            raise serializers.ValidationError(
                "Нельзя подписаться на самого себя"
            )
        return data

    def validate_recipes_limit(self, value):
        """Валидация параметра recipes_limit."""
        try:
            limit = int(value)
            if limit < 0:
                raise serializers.ValidationError(
                    "recipes_limit должен быть положительным числом"
                )
            return limit
        except (ValueError, TypeError):
            raise serializers.ValidationError(
                "recipes_limit должен быть целым числом"
            )

    def get_recipes(self, obj):
        recipes = obj.recipes.all()
        recipes_limit = self.context.get(
            'request'
        ).query_params.get('recipes_limit')
        if recipes_limit is not None:
            limit = self.validate_recipes_limit(recipes_limit)
            recipes = recipes[:limit]
        return RecipeShortSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Recipe.objects.filter(author=obj.id).count()


class FollowSerializer(serializers.ModelSerializer):

    class Meta:
        model = Follow
        fields = ('user', 'author')

    def validate(self, subscribe):
        user = subscribe.get('user')
        author = subscribe.get('author')
        request = self.context['request']
        exists = user.subscriptions.filter(author=author).exists()
        if request.method == 'POST' and exists:
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя!'
            )
        if request.method == 'DELETE' and not exists:
            raise serializers.ValidationError(
                'Вы не подписаны на этого пользователя,'
                ' поэтому удаление подписки невозможно!'
            )
        if user.id == author.id:
            raise serializers.ValidationError('Нельзя подписаться на себя!')
        return subscribe

    def to_representation(self, instance):
        """Метод представления модели."""
        return UserFollowSerializer(
            instance.author,
            context={'request': self.context.get('request')}
        ).data


class ShortLinkSerializer(serializers.ModelSerializer):
    """Сериализатор для коротких ссылок на рецепты."""

    short_link = serializers.CharField(max_length=256, source='shortcode')

    class Meta:
        model = ShortUrl
        fields = ('short_link',)
