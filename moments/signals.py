from django.db.models.signals import post_save
from notifications.signals import notify

from moments.models import Report, ReviewMoment, ReviewStory, StoryReport
from user.utils import get_recipients_of_admin_realtime_notification


def moment_report_handler(sender, instance, created, **kwargs):
    recipients = get_recipients_of_admin_realtime_notification()
    description = f"ID:{instance.id} | Reporter: {instance.user} | Report msg: {instance.Report_msg}"
    notify.send(instance, recipient=recipients, verb='A moment was reported', description=description, event_type='REPORT_MOMENT')

def story_report_handler(sender, instance, created, **kwargs):
    recipients = get_recipients_of_admin_realtime_notification()
    description = f"ID:{instance.id} | Reporter: {instance.user} | Report msg: {instance.Report_msg}"
    notify.send(instance, recipient=recipients, verb='A story was reported', description=description, event_type='REPORT_STORY')

def moment_review_handler(sender, instance, created, **kwargs):
    recipients = get_recipients_of_admin_realtime_notification()
    description = f'ID: {instance.id} | title: {instance.title} | Moment detected for review'
    verb = f"A moment by {instance.user.email} detected for admin review"
    notify.send(instance, recipient=recipients, verb=verb, description=description, event_type="REVIEW_MOMENT")


def story_review_handler(sender, instance, created, **kwargs):
    recipients = get_recipients_of_admin_realtime_notification()
    description = f'ID: {instance.id} | Story detected for review'
    verb = f"A story by {instance.user.email} detected for admin review"
    notify.send(instance, recipient=recipients, verb=verb, description=description, event_type="REVIEW_STORY")


post_save.connect(moment_report_handler, sender=Report)
post_save.connect(story_report_handler, sender=StoryReport)

post_save.connect(moment_review_handler, sender=ReviewMoment)
post_save.connect(story_review_handler, sender=ReviewStory)
