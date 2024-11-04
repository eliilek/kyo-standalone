from django.urls import path, include
from django.contrib import admin
from kyoapp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('join', views.join, name='join'),
    path('signup', views.signup, name='signup'),
    path('download', views.download_select, name='download_select'),
    path('download/<int:game_pk>', views.download, name='download'),
    path('game/<slug:slug>', views.manage_game, name='manage_game'),
    path('queued', views.queued, name='queued'),
    path('retrieve/<str:filename>', views.retrieve, name='retrieve'),
    path('delete/<str:filename>', views.delete, name='delete'),
    path('django-rq/', include('django_rq.urls')),
]

urlpatterns += [
    path(r'accounts/', include('django.contrib.auth.urls')),
]