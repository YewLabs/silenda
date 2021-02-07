import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'silenda.settings.' + os.environ.setdefault('DJANGO_ENV', 'base'))

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import nuntius.routing
import hunt.routing

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(
            nuntius.routing.websocket_urlpatterns +
            hunt.routing.websocket_urlpatterns
        )
    ),
})
