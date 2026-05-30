from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView

from .forms import CommentForm, PostForm, UserForm
from .models import Category, Comment, Post, User

NUM_POST = 10


class OnlyAuthorMixin(UserPassesTestMixin):
    """Миксин для проверки авторства публикаций."""

    def test_func(self):
        return self.get_object().author == self.request.user


def prepare_posts(posts=Post.objects, published=True,
                  related=True, commented=True):
    """Функция, предназначеная для подготовки публикаций.

    Пост отображается на страницах проекта, если у него одновременно:
      * дата публикации — не позже текущего времени,
      * он опубликован,
      * категория, к которой он принадлежит, не снята с публикации.
    Кроме того, функция позволяет добавить к публикациям информацию
    о количестве комментариев, а также извлекать из БД поля
    связанных моделей.
    """
    if published:
        posts = posts.filter(
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True
        )
    if related:
        posts = posts.select_related('author', 'category', 'location')
    if commented:
        posts = posts.annotate(
            comment_count=Count('comments')
        ).order_by(*Post._meta.ordering)
    return posts


def paginate(request, posts, count_post=NUM_POST):
    return Paginator(posts, count_post).get_page(request.GET.get('page'))


def index(request):
    """View-функция для формирования главной страницы.

    На главной странице должны показываться только те публикации,
    у которых одновременно:
    * дата публикации — не позже текущего времени,
    * значение поля is_published равно True,
    * у категории, к которой принадлежит публикация,
    значение поля is_published равно True.
    """
    return render(request, 'blog/index.html', {
        'page_obj': paginate(request, prepare_posts()),
    })


def post_detail(request, post_id):
    """View-функция для формирования страницы отдельной публикации.

    Выводится отдельная публикация, полученная по первичному ключу.
    Запрос к странице публикации должен вернуть ошибку 404, если:
    * дата публикации — позже текущего времени
    * или значение поля is_published у запрошенной публикации равно False,
    * или у категории, к которой принадлежит публикация,
    значение поля is_published равно False.
    """
    post = get_object_or_404(Post.objects, pk=post_id)
    if post.author != request.user:
        post = get_object_or_404(prepare_posts(
            commented=False, related=False,
        ), pk=post_id)
    return render(request, 'blog/detail.html', {
        'post': post,
        'form': CommentForm(),
        'comments': post.comments.select_related('author'),
    })


def category_posts(request, category_slug):
    """View-функция для формирования страницы выбранной категории.

    Выводятся только те публикации, которые:
    * принадлежат выбранной категории,
    * значение поля is_published равно True,
    * дата публикации — не позже текущего времени.
    Если у запрошенной категории значение поля is_published равно False —
    должна возвращаться ошибка 404.
    """
    category = get_object_or_404(Category, is_published=True,
                                 slug=category_slug)
    return render(request, 'blog/category.html', {
        'page_obj': paginate(request, prepare_posts(category.posts)),
        'category': category,
    })


class PostCreateView(LoginRequiredMixin, CreateView):
    """CBV для создания публикации."""

    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def get_success_url(self):
        return reverse(
            'blog:profile',
            args=[self.request.user.username]
        )

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class PostMixin:
    """Миксин для редактирования и удаления публикаций."""

    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'


class PostUpdateView(OnlyAuthorMixin, PostMixin, UpdateView):
    """CBV для редактирования публикации."""

    form_class = PostForm

    def handle_no_permission(self):
        return redirect(self.get_object().get_absolute_url())


class PostDeleteView(OnlyAuthorMixin, PostMixin, DeleteView):
    """CBV для удаления публикации."""

    success_url = reverse_lazy('blog:index')

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs,
                                        form=CommentForm(instance=self.object))


class UserDetailView(DetailView):
    """CBV для отображения страницы пользователя."""

    model = User
    template_name = 'blog/profile.html'
    context_object_name = 'profile'
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, **kwargs):
        posts = prepare_posts(self.object.posts,
                              published=(self.object != self.request.user))
        return super().get_context_data(**kwargs,
                                        page_obj=paginate(self.request, posts))


@login_required
def edit_profile(request):
    """View-функция для редактирования профиля пользователя."""
    form = UserForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
    return render(request, 'blog/user.html', {
        'form': form,
    })


@login_required
def add_comment(request, post_id):
    """View-функция для добавления комментариев к публикациям."""
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = get_object_or_404(Post, pk=post_id)
        comment.save()
    return redirect('blog:post_detail', post_id)


class CommentMixin:
    """Миксин для редактирования и удаления комментариев."""

    model = Comment
    template_name = 'blog/comment.html'
    success_url = reverse_lazy('blog:index')
    pk_url_kwarg = 'comment_id'


class CommentUpdateView(CommentMixin, OnlyAuthorMixin, UpdateView):
    """CBV для редактирования комментариев к публикациям."""

    form_class = CommentForm

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, comment=self.object)


class CommentDeleteView(CommentMixin, OnlyAuthorMixin, DeleteView):
    """CBV для удаления комментариев к публикациям."""
