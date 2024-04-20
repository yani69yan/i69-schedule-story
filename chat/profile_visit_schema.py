import graphene
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from chat.schema_helpers import is_user_logged_in, profile_visiting

User = get_user_model()


class ProfileVisit(graphene.Mutation):
    is_visited = graphene.Boolean()
    is_notification_sent = graphene.Boolean()

    class Arguments:
        visiting = graphene.String(required=True)
        visitor = graphene.String()

    @classmethod
    def mutate(cls, root, info, visiting, visitor=None):
        user = info.context.user
        is_user_logged_in(user, raise_exception=True)

        if user.is_worker and visitor:
           visitor = get_object_or_404(User, id=visitor)
           visitor = visitor
        else:
            visitor = user

        visiting = get_object_or_404(User, id=visiting)

        is_visited, is_notification_sent = profile_visiting(visitor, visiting, True)

        return ProfileVisit(is_visited=is_visited, is_notification_sent=is_notification_sent)