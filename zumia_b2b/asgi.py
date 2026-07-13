# import os

# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# from home import routing

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zumia_b2b.settings')

# # application = get_asgi_application()

# # os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbackend.settings')

# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             routing.websocket_urlpatterns
#         )
#     ),
# })

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from home.middleware import JWTAuthMiddleware
from home import routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zumia_b2b.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,

    "websocket": JWTAuthMiddleware(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})
