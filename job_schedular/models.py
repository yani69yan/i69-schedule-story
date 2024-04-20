from django.db import models


class JobPublisherManager(models.Manager):

    def published(self):
        return self.filter(is_published=True)

    def unpublished(self):
        return self.filter(is_published=False)


class JobPublisher(models.Model):

    is_published = models.BooleanField(default=True)
    publish_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        abstract = True

    objects = JobPublisherManager()