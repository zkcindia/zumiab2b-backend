# from channels.generic.websocket import AsyncWebsocketConsumer
# import json

# class CartNotificationConsumer(AsyncWebsocketConsumer):

#     async def connect(self):
#         self.group_name = "cart_updates"

#         await self.channel_layer.group_add(
#             self.group_name,
#             self.channel_name
#         )

#         await self.accept()

#         print("✅ Cart WebSocket CONNECTED")

#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard(
#             self.group_name,
#             self.channel_name
#         )

#         print("❌ Cart WebSocket DISCONNECTED")

#     async def notify(self, event):
#         await self.send(text_data=json.dumps(event["message"]))



from channels.generic.websocket import AsyncWebsocketConsumer
import json


from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Sum
from .models import Cart, CartItem
import json


class CartNotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        await self.accept()

        self.group_name = "cart_updates"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        cart_count = await self.get_cart_count()

        await self.send(text_data=json.dumps({
            "type": "cart_count",
            "count": cart_count
        }))

        print("✅ Cart WebSocket Connected")

    async def disconnect(self, close_code):

        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

        print("❌ Cart WebSocket Disconnected")

    async def notify(self, event):

        await self.send(
            text_data=json.dumps(event["message"])
        )

    @database_sync_to_async
    def get_cart_count(self):

        user = self.scope.get("user")

        if not user or user.is_anonymous:
            return 0

        cart = Cart.objects.filter(user=user).first()

        print("CART =>", cart)

        if not cart:
            return 0

        print("ITEMS =>", cart.items.count())

        return cart.items.count()