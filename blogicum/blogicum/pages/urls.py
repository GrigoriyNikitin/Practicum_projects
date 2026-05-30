from django.urls import path

from .views import AboutPageView, RulesPageView

app_name = 'pages'

urlpatterns = [
    path('about/', AboutPageView.as_view(), name='about'),
    path('rules/', RulesPageView.as_view(), name='rules'),
]
