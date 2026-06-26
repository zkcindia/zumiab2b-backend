"""
WSGI config for zumia_b2b project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

# import os

# from django.core.wsgi import get_wsgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zumia_b2b.settings')

# application = get_wsgi_application()


import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from home import routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'store_management.settings')

# application = get_asgi_application()

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbackend.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})
