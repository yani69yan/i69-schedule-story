from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from rest_framework.authtoken.models import Token


@database_sync_to_async
def get_user(token_key):
    try:
        token = Token.objects.get(key=token_key)
        #print("token user: ", token.user.username)
        close_old_connections()
        return token.user
    except Token.DoesNotExist:
        #print("token user: not found ")
        return AnonymousUser()
    except Exception as e:
        pass
        #print("token user: some other error: ", e)
    return AnonymousUser()


class i69TokenAuthMiddleware:
    """
    Token authorization middleware for Django Channels 3
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        try:
            token_key = (
                dict((x.split("=") for x in scope["query_string"].decode().split("&")))
            ).get("token", None)
            #print("token key", token_key)
        except ValueError:
            token_key = None
        scope["user"] = (
            AnonymousUser() if token_key is None else await get_user(token_key)
        )
        #print("token user2: ", scope["user"].username)
        return await self.inner(scope, receive, send)


i69TokenAuthMiddlewareStack = lambda inner: i69TokenAuthMiddleware(
    AuthMiddlewareStack(inner)
)

import logging

logger = logging.getLogger('django')

import time

class RequestLoggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Call the next middleware or view
        response = self.get_response(request)

        # Log information about the incoming request
        self.log_request(request, response)

        return response

    def log_request(self, request, response):
        method = request.method
        path = request.path
        status_code = response.status_code
        referer = request.META.get('HTTP_REFERER', '')

        msg = f"HTTP {method} {path} {status_code} {referer}"

        logger.info(msg)

