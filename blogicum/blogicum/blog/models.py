from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse

User = get_user_model()

WORD_LENGHT = 20


class CreatedPublishedModel(models.Model):
    """Абстрактная модель.

    Добавляет к модели дату создания и последнего изменения,
    а также добвляет флаг is_published.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Добавлено'
    )
    is_published = models.BooleanField(
        default=True,
        verbose_name='Опубликовано',
        help_text='Снимите галочку, чтобы скрыть публикацию.'
    )

    class Meta:
        abstract = True


class Category(CreatedPublishedModel):
    """Модель с категориями.

    К одной категории может принадлежать несколько публикаций.
    """

    title = models.CharField(max_length=256, verbose_name='Заголовок')
    description = models.TextField(verbose_name='Описание')
    slug = models.SlugField(
        unique=True,
        verbose_name='Идентификатор',
        help_text='Идентификатор страницы для URL; разрешены символы'
                  ' латиницы, цифры, дефис и подчёркивание.'
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'Категории'
        ordering = ('title',)

    def __str__(self):
        return self.title[:WORD_LENGHT]


class Location(CreatedPublishedModel):
    """Модель с местоположениями.

    К одному местоположению может принадлежать несколько публикаций.
    Местоположение может быть не указано для публикации, тогда в качестве
    локации на страницах проекта будет отображаться значение «Планета Земля».
    """

    name = models.CharField(max_length=256, verbose_name='Название места')

    class Meta:
        verbose_name = 'местоположение'
        verbose_name_plural = 'Местоположения'
        ordering = ('name',)

    def __str__(self):
        return self.name[:WORD_LENGHT]


class Post(CreatedPublishedModel):
    """Модель с публикациями.

    Главное в блоге — это публикация («пост»), вокруг неё всё и строится.
    """

    title = models.CharField(max_length=256, verbose_name='Заголовок')
    text = models.TextField(verbose_name='Текст')
    pub_date = models.DateTimeField(
        verbose_name='Дата и время публикации',
        help_text='Если установить дату и время в будущем — можно делать'
                  ' отложенные публикации.'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор публикации',
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Местоположение'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Категория'
    )
    image = models.ImageField(
        'Изображение',
        upload_to='posts_images',
        blank=True
    )

    class Meta:
        default_related_name = 'posts'
        verbose_name = 'публикация'
        verbose_name_plural = 'Публикации'
        ordering = ('-pub_date',)

    def __str__(self):
        return self.title[:WORD_LENGHT]

    def get_absolute_url(self):
        return reverse('blog:post_detail', args=[self.pk])


class Comment(models.Model):
    """Модель с комментариями.

    Комментарии должны быть отсортированы по времени их публикации,
    «от старых к новым».
    Комментарии могут оставлять только авторизованные пользователи.
    """

    text = models.TextField('Текст')
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        verbose_name='Публикация'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор'
    )

    class Meta:
        default_related_name = 'comments'
        verbose_name = 'комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ('created_at',)

    def __str__(self):
        return self.text[:WORD_LENGHT]
