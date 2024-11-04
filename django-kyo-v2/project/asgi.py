import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
import django
django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import kyoapp.routing

application = ProtocolTypeRouter({
  "https": get_asgi_application(),
  "http": get_asgi_application(),
  "websocket": AuthMiddlewareStack(
        URLRouter(
            kyoapp.routing.websocket_urlpatterns
        )
    ),
})