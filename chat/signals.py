from django.db.models.signals import post_save
from notifications.signals import notify

from chat.models import ContactUs
from user.utils import get_recipients_of_admin_realtime_notification


def contact_us_handler(sender, instance, created, **kwargs):
    recipients = get_recipients_of_admin_realtime_notification()
    description = f"ID: {instance.email} | Contacted us"
    verb = f"{instance.name if instance.name else instance.email} contacted us at {instance.created_at}"
    notify.send(instance, recipient=recipients, verb=verb, description=description, event_type="CONTACT_US")


post_save.connect(contact_us_handler, sender=ContactUs)