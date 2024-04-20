from django.db.models.signals import post_save
from notifications.signals import notify

from user.models import ReviewUserPhoto, User, UserInterestForRegion, UserProfileTranlations
from user.schema import (HideInterestedInSubscription,
                         UserProfileTranslationSubscription)
from user.utils import get_recipients_of_admin_realtime_notification


def new_user_handler(sender, instance, created, **kwargs):
    if created:
        recipients = get_recipients_of_admin_realtime_notification()
        description = f"ID:{instance.id} | Email: {instance.email}"
        notify.send(instance, recipient=recipients, verb='A new user has joined', description=description, event_type='NEW_USER')

post_save.connect(new_user_handler, sender=User)


def hide_interested_in_handler(sender, instance, created, **kwargs):
    if created:
        HideInterestedInSubscription.broadcast(
            group='hide_interested_in_subscription',
            payload={'user_interestedIn_instance': instance}
        )


def update_hide_interested_in_handler(sender, instance, **kwargs):
    HideInterestedInSubscription.broadcast(
        group='hide_interested_in_subscription',
        payload={'user_interestedIn_instance': instance}
    )

post_save.connect(hide_interested_in_handler, sender=UserInterestForRegion)
post_save.connect(update_hide_interested_in_handler, sender=UserInterestForRegion)


def add_user_profile_translation_handler(sender, instance, created, **kwargs):
    if created:
        UserProfileTranslationSubscription.broadcast(
            group='user_profile_translation_subscription',
            payload={'user_profile_translation_instance': instance}
        )


def update_user_profile_translation_handler(sender, instance, **kwargs):
    UserProfileTranslationSubscription.broadcast(
        group='user_profile_translation_subscription',
        payload={'user_profile_translation_instance': instance}
    )

post_save.connect(add_user_profile_translation_handler, sender=UserProfileTranlations)
post_save.connect(update_user_profile_translation_handler, sender=UserProfileTranlations)


def userphoto_review_handler(sender, instance, created, **kwargs):
    recipients = get_recipients_of_admin_realtime_notification()
    description = f"ID: {instance.id} | User Photo detected for Admin Review."
    verb = f"A User Photo by {instance.user_photo.user.email} is detected for Admin Review."
    notify.send(instance, recipient=recipients, verb=verb, description=description, event_type="REVIEW_USERPHOTO")


post_save.connect(userphoto_review_handler, sender=ReviewUserPhoto)
