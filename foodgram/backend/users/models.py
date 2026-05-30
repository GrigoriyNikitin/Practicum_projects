from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from recipes.constants import EMAIL_MAX_LENGTH, USER_MAX_LENGTH


class User(AbstractUser):
    """Кастомная модель пользователя (добавлено поле avatar)."""

    email = models.EmailField(
        max_length=EMAIL_MAX_LENGTH,
        unique=True,
        verbose_name='Электронная почта'
    )
    username = models.CharField(
        max_length=USER_MAX_LENGTH,
        unique=True,
        db_index=True,
        verbose_name='Имя пользователя',
        validators=(UnicodeUsernameValidator(),)
    )
    first_name = models.CharField(
        max_length=USER_MAX_LENGTH,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=USER_MAX_LENGTH,
        verbose_name='Фамилия'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        default='avatars/default_avatar.jpg',
        verbose_name='Аватар')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username
