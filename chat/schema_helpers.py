from datetime import datetime

from chat.constants import PROFILE_VISIT_NOTIFICATION_SETTING
from chat.models import Notification, send_notification_fcm
from user.models import ProfileVisit
from user.utils import translate_error_message


def is_user_logged_in(user, raise_exception=False):
    if not user or not user.is_authenticated:
        if raise_exception:
            raise Exception(translate_error_message(user, "You need to be logged in to chat"))
        else:
            return False

    return True


def profile_visiting(visitor, visiting, broadcast_visit=True):
    if visitor.id == visiting.id or visitor.is_admin:
        return False, False

    profile_visit, is_created = ProfileVisit.objects.get_or_create(
        visitor=visitor,
        visiting=visiting,
    )

    if not is_created and not profile_visit.can_notify_profile_visit:
        return True, False

    profile_visit.last_visited_at = datetime.now()
    profile_visit.save()

    try:
        icon = visitor.avatar().file.url
    except:
        icon = None

    data = {
        "notification_type": PROFILE_VISIT_NOTIFICATION_SETTING,
        "visited_user_id": str(visitor.id)
    }

    notification, is_created = Notification.objects.get_or_create(
        user=visiting,
        sender=visitor,
        notification_setting_id=PROFILE_VISIT_NOTIFICATION_SETTING,
        defaults={
            "data": data
        }
    )
    if not is_created:
        notification.sender = visitor
        notification.user = visiting
        notification.created_date = profile_visit.last_visited_at
        notification.data = data
        notification.save()

    send_notification_fcm(notification, icon=icon, image=icon)
    if broadcast_visit:
        from user.schema import ProfileVisitSubscription

        ProfileVisitSubscription.broadcast(
            group=f"{visiting.id}",
            payload={'profile_visit_instance': profile_visit}
        )

    return True, True