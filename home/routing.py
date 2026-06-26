from django.urls import path
from .consumers import CartNotificationConsumer

websocket_urlpatterns = [
    path("ws/cart/", CartNotificationConsumer.as_asgi()),
]