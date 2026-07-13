from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware

from rest_framework_simplejwt.tokens import AccessToken

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

User = get_user_model()


@database_sync_to_async
def get_user(token):

    try:
        if not token:
            return AnonymousUser()

        access_token = AccessToken(token)

        user_id = access_token["user_id"]

        return User.objects.get(id=user_id)

    except Exception as e:
        print("JWT Error:", e)
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):

    async def __call__(self, scope, receive, send):

        headers = dict(scope["headers"])

        auth_header = headers.get(b"authorization")

        token = None

        # For Postman / custom clients
        if auth_header:

            try:
                auth_header = auth_header.decode("utf-8")

                if auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]

            except Exception as e:
                print("Header parsing error:", e)

        # For React browser clients
        if not token:

            try:
                query_string = scope["query_string"].decode()

                query_params = parse_qs(query_string)

                token = query_params.get(
                    "token",
                    [None]
                )[0]

            except Exception as e:
                print("Query parsing error:", e)

        scope["user"] = await get_user(token)

        print("Authenticated User =>", scope["user"])

        return await super().__call__(
            scope,
            receive,
            send
        )