from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<slug>\w+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/results/(?P<slug>\w+)/$', consumers.MoveConsumer.as_asgi()),
    re_path(r'ws/super/$', consumers.SuperConsumer.as_asgi()),
]