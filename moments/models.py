import json
import logging
import uuid

from django.contrib.contenttypes.fields import (GenericForeignKey,
                                                GenericRelation)
from django.contrib.contenttypes.models import ContentType
from django.db import models
from push_notifications.models import GCMDevice
from chat.constants import MOMENT_SHARED_NOTIFICATION_SETTING, STORY_SHARED_NOTIFICATION_SETTING
from chat.models import Notification, send_notification_fcm
from job_schedular.models import JobPublisher

from user.models import ChatsQue, User
from user.utils import disable_fcm_device_by_registration_id

LOGGER = logging.getLogger("moment_models")


class GenericLike(models.Model):
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="likes"
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    user = models.ForeignKey(User, related_name="user_likes", on_delete=models.CASCADE)


class GenericComment(models.Model):
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="comments"
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    user = models.ForeignKey(
        User, related_name="user_comments", on_delete=models.CASCADE
    )
    comment_description = models.CharField(max_length=100, null=True)
    created_date = models.DateTimeField(auto_now_add=True, null=True)
    likes = GenericRelation(GenericLike)


class Story(JobPublisher):
    def get_avatar_path(self, filename):
        ext = filename.split(".")[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return "static/uploads/stories/" + filename

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to=get_avatar_path, max_length=1000)
    thumbnail = models.ImageField(upload_to=get_avatar_path, blank=True, null=True)
    likes = GenericRelation(GenericLike)
    comments = GenericRelation(GenericComment)

    def post_save(self, context=None):
        """Send notification to the followed User about the Story that Logged-In user shared"""
        from moments.schema import OnNewStory

        muser = self.user
        followers = muser.user_following.all()

        try:
            avatar_url = muser.avatar().file.url
            icon = context.build_absolute_uri(avatar_url)
        except:
            icon = None

        for follower in followers:
            moderator = ChatsQue.objects.filter(worker=muser, isAssigned=True).first()
            if not moderator:
                LOGGER.info(f"OnNewStory broadcasted. user_id: {self.user.id} - story_id: {self.id}")
                OnNewStory.broadcast(
                    group=None,
                    payload={"user_id": str(self.user.id), "story_id": self.id},
                )
                return muser

            moderator = moderator.moderator
            data = {
                "momentId": self.id,
                "notification_type": STORY_SHARED_NOTIFICATION_SETTING,
            }
            notification_obj = Notification(
                user=follower.follower,
                sender=moderator,
                app_url=None,
                notification_setting_id=STORY_SHARED_NOTIFICATION_SETTING,
                data=data,
                priority=None,
            )
            send_notification_fcm(
                notification_obj=notification_obj,
                android_channel_id=None,
                icon=icon,
                image=icon
            )

        LOGGER.info(f"OnNewStory broadcasted. user_id: {self.user.id} - story_id: {self.id}")
        OnNewStory.broadcast(
            group=None,
            payload={"user_id": str(self.user.id), "story_id": self.id},
        )


class Moment(JobPublisher):
    def get_avatar_path(self, filename):
        ext = filename.split(".")[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return "static/uploads/moments/" + filename

    user = models.ForeignKey(
        User, related_name="User_for_moments", on_delete=models.CASCADE
    )
    Title = models.CharField(max_length=100, null=True)
    moment_description = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)
    file = models.FileField(
        upload_to=get_avatar_path, null=True, blank=True, max_length=1000
    )
    allow_comment = models.BooleanField(default=True)

    def post_save(self, context=None):
        """Send notification to the followed User about the Moment that Logged-In user shared"""
        from moments.schema import NotifyNewMoment

        muser = self.user
        followers = muser.user_following.all()

        try:
            avatar_url = muser.avatar().file.url
            icon = context.build_absolute_uri(avatar_url)
        except:
            icon = None

        for follower in followers:
            try:
                moderator = ChatsQue.objects.filter(worker=muser, isAssigned=True).first().moderator
            except:
                LOGGER.info(f"OnNewMoment broadcasted. user_id: {self.user.id} - moment_id: {self.id}")
                NotifyNewMoment.broadcast(payload=self, group="moments")
                return muser

            data = {
                "momentId": self.id,
                "notification_type": MOMENT_SHARED_NOTIFICATION_SETTING,
            }
            notification_obj = Notification(
                user=follower.follower,
                sender=moderator,
                app_url=None,
                notification_setting_id=MOMENT_SHARED_NOTIFICATION_SETTING,
                data=data,
                priority=None,
            )
            send_notification_fcm(
                notification_obj=notification_obj,
                android_channel_id=None,
                icon=icon,
                image=icon
            )

        LOGGER.info(f"OnNewMoment broadcasted. user_id: {self.user.id} - moment_id: {self.id}")
        NotifyNewMoment.broadcast(payload=self, group="moments")

    def __str__(self):
        return str(self.Title)


class Like(models.Model):
    user = models.ForeignKey(
        User, related_name="User_for_like", on_delete=models.CASCADE
    )
    momemt = models.ForeignKey(
        Moment, related_name="momemt_for_like", on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class Comment(models.Model):
    user = models.ForeignKey(
        User, related_name="User_for_comment", on_delete=models.CASCADE
    )
    comment_description = models.TextField()
    momemt = models.ForeignKey(
        Moment, related_name="momemt_for_comment", on_delete=models.CASCADE
    )
    created_date = models.DateTimeField(auto_now_add=True, null=True)
    reply_to = models.ForeignKey(
        "self",
        related_name="parent_comment",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class CommentLike(models.Model):
    user = models.ForeignKey(User, related_name="likers", on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)

class ReportComment(models.Model):
    user = models.ForeignKey(
        User, related_name="User_for_report_comment", on_delete=models.CASCADE
    )
    Report_msg = models.TextField()
    comment = models.ForeignKey(
        Comment, related_name="comment_for_report", on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            str(self.user)
            + " - "
            + str(self.Report_msg)
            + " ---- "
            + str(self.timestamp)
        )

class Report(models.Model):
    user = models.ForeignKey(
        User, related_name="User_for_report", on_delete=models.CASCADE
    )
    Report_msg = models.TextField()
    momemt = models.ForeignKey(
        Moment, related_name="momemt_for_report", on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            str(self.user)
            + " - "
            + str(self.Report_msg)
            + " ---- "
            + str(self.timestamp)
        )


class StoryReport(models.Model):
    user = models.ForeignKey(
        User, related_name="User_for_story_report", on_delete=models.CASCADE
    )
    Report_msg = models.TextField()
    story = models.ForeignKey(
        Story, related_name="story_for_report", on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            str(self.user)
            + " - "
            + str(self.Report_msg)
            + " ---- "
            + str(self.timestamp)
        )


class StoryVisibleTime(models.Model):
    text = models.CharField(" ", max_length=20, default="Click to change")
    weeks = models.IntegerField(default=0)
    days = models.IntegerField(default=3)
    hours = models.IntegerField(default=1)
    # hours = models.DecimalField(max_digits = 2,decimal_places = 2, null=True)

    def __str__(self):
        return str(self.weeks) + "-" + str(self.days) + "-" + str(self.hours)


def send_moment_broadcast_fcm(
    moment_obj, android_channel_id=None, icon=None, image=None, **kwargs
):
    user = moment_obj.user
    #print("share memont user ", user)
    fcm_devices = GCMDevice.objects.all().distinct("registration_id").exclude(user=user)

    #print("all fcm devices ", fcm_devices)
    title = "New Moment added"
    body = f"{user.fullName} added new Moment.."
    img_url = None
    # checks for avatar_url if None
    try:
        img_url = moment_obj.file.url
    except:
        img_url = None
    # if img_url:
    #     icon=info.context.build_absolute_uri(img_url)
    data = {"notification_type": "SM",
            "img_url": img_url,
            "moment_id": moment_obj.id
            }
    #print("sending notifications to all")
    try:
        resp = fcm_devices.send_message(
            body,
            badge=1,
            sound="default",
            extra={"title": title, "icon": icon, "data": data, "image": image},
        )
        #print(f"Share Moment FCM: {resp}")
    except Exception as ex:
        ex = str(ex).replace("'", "\"")
        fcm_messages = json.loads(ex)
        for msg in fcm_messages['results']:
            if "error" in msg:
                #print('FCM message failed. Error:', msg['error'], ', Registration ID:', msg['original_registration_id'])
                disable_fcm_device_by_registration_id(msg['original_registration_id'], msg['error'])

class ReviewStory(models.Model):
    def get_file_review_avatar_path(self, filename):
        ext = filename.split(".")[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return "static/uploads/story/reviews/" + filename

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    file = models.FileField(
        upload_to=get_file_review_avatar_path, null=True, blank=True
    )
    thumbnail = models.ImageField(
        upload_to=get_file_review_avatar_path, blank=True, null=True
    )
    file_type = models.CharField(
        max_length=10,
        choices=(
            ("image", "image"),
            ("video", "video"),
        ),
    )
    prediction_score = models.CharField(
        default="", null=True, blank=True, max_length=255
    )


class ReviewMoment(models.Model):
    def get_file_review_avatar_path(self, filename):
        ext = filename.split(".")[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return "static/uploads/moment/reviews/" + filename

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100, null=True)
    moment_description = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)
    file = models.FileField(
        upload_to=get_file_review_avatar_path, null=True, blank=True
    )

    file_type = models.CharField(
        max_length=10,
        choices=(
            ("image", "image"),
            ("video", "video"),
        ),
    )
    prediction_score = models.CharField(
        default="", null=True, blank=True, max_length=255
    )
