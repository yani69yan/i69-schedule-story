from celery import shared_task
from django.utils import timezone
import logging

from moments.models import Moment, Story

LOGGER = logging.getLogger("schedular_logger")

def publish_jobs(jobs):
    for job in jobs:
        if job.publish_at <= timezone.now():
            LOGGER.info(f"job: {job.id} from {type(job)} is published")
            #print(f"job: {job.id} from {type(job)} is published")
            job.is_published = True
            job.save()
            if getattr(job, 'post_save'):
                LOGGER.info("post save called")
                #print("post save called")
                job.post_save()


@shared_task(name="moment_job_publisher")
def moment_job_publisher(*args, **kwargs):
    unpub_moments = Moment.objects.unpublished().all()
    publish_jobs(unpub_moments)


@shared_task(name="story_job_publisher")
def story_job_publisher(*args, **kwargs):
    unpub_storys = Story.objects.unpublished().all()
    publish_jobs(unpub_storys)
