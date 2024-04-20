import datetime
import mimetypes
import os
import re

import cv2
import opennsfw2 as n2
import pytesseract
from django.db.models import F, Q
from django.utils import timezone

from chat.models import Notification, send_notification_fcm
from moments.constants import (FACE_DETECTION_FEATURE, TEXT_DETECTION_FEATURE,
                               USER_FACE_DETECTION_FEATURE,
                               USER_NSFW_DETECTION_FEATURE,
                               USER_TEXT_DETECTION_FEATURE)
from moments.models import ReviewMoment, ReviewStory, Story, StoryVisibleTime
from purchase.models import PackagePurchase
from user.models import (BlockedImageAlternatives, ReviewUserPhoto, User,
                         UserLimit, UserPhoto)
from user.utils import is_feature_enabled, translate_error_message


def detect_face(tempfile_name):
    face_cascade = cv2.CascadeClassifier("frontface-detection.xml")
    face = face_cascade.detectMultiScale(
        cv2.cvtColor(cv2.imread(tempfile_name), cv2.COLOR_BGR2GRAY), 1.2, 4
    )
    return bool(len(face))


def detect_face_using_haarcascade(file_path):
    img = cv2.imread(file_path)
    gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_classifier = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    profile_face_classifier = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_profileface.xml"
    )
    frontal_face = face_classifier.detectMultiScale(
        gray_image, scaleFactor=1.2, minNeighbors=4,
    )
    profile_face = profile_face_classifier.detectMultiScale(
        gray_image, scaleFactor=1.2, minNeighbors=4,
    )
    return bool(len(frontal_face)) or bool(len(profile_face))


def detect_text_in_image(file_path):
    img_text = pytesseract.image_to_string(file_path)
    img_text = ''.join(img_text.split())
    return len(re.findall(r'[0-9A-Za-z]', img_text)) > 7


def detect_video(path):
    result = False
    video = cv2.VideoCapture(path)
    success, image = video.read()
    count = 0
    frame_rate = video.get(5)

    while success:
        cv2.imwrite(f"frame{count}.jpg", image)
        prediction_score = n2.predict_image(f"frame{count}.jpg")

        if prediction_score > 0.5:
            result = True
            os.remove(f"frame{count}.jpg")
            break
        else:
            os.remove(f"frame{count}.jpg")
            count += 1
            video.set(cv2.CAP_PROP_POS_FRAMES, int(frame_rate * 30 * count))
            success, image = video.read()
    return result, prediction_score


def detect_story(obj, file):
    filetype = mimetypes.guess_type(str(obj.file.url))[0].split("/")[0]
    result = False
    face_detection = True
    text_detection = False
    # save temp file
    tempfile_name = f"/tmp/{file.name}"
    with open(tempfile_name, "wb") as tempfile:
        tempfile.write(obj.file.read())

    if filetype == "video":
        file_type = "video"
        result, prediction_score = detect_video(tempfile_name)
    else:
        file_type = "image"

        if is_feature_enabled(FACE_DETECTION_FEATURE):
            face_detection = detect_face_using_haarcascade(tempfile_name)

        if is_feature_enabled(TEXT_DETECTION_FEATURE):
            text_detection = detect_text_in_image(tempfile_name)

        prediction_score = n2.predict_image(tempfile_name)
        result = prediction_score > 0.5

    if result or not face_detection or text_detection:
        ReviewStory.objects.create(
            user=obj.user,
            file_type=file_type,
            file=obj.file,
            thumbnail=obj.thumbnail,
            prediction_score=prediction_score,
        )
        obj.delete()
    # delete temp file
    os.remove(tempfile_name)
    return result or not face_detection or text_detection


def detect_moment(obj, file):
    filetype = mimetypes.guess_type(str(obj.file.url))[0].split("/")[0]
    result = False
    face_detection = True
    text_detection = False
    # save temp file
    tempfile_name = f"/tmp/{file.name}"
    with open(tempfile_name, "wb") as tempfile:
        tempfile.write(obj.file.read())

    if filetype == "video":
        file_type = "video"
        result, prediction_score = detect_video(tempfile_name)
    else:
        file_type = "image"
        if is_feature_enabled(FACE_DETECTION_FEATURE):
            face_detection = detect_face_using_haarcascade(tempfile_name)

        if is_feature_enabled(TEXT_DETECTION_FEATURE):
            text_detection = detect_text_in_image(tempfile_name)

        prediction_score = n2.predict_image(tempfile_name)
        result = prediction_score > 0.5

    if result or not face_detection or text_detection:
        ReviewMoment.objects.create(
            user=obj.user,
            file_type=file_type,
            file=obj.file,
            title=obj.Title,
            moment_description=obj.moment_description,
            prediction_score=prediction_score,
        )
        obj.delete()
        # delete temp file
        os.remove(tempfile_name)
        return result or not face_detection or text_detection


def detect_user_image(obj):
    if obj.is_admin_approved:
        return

    tempfile_name = f"/tmp/{obj.file.name.split('/')[-1]}"
    with open(tempfile_name, "wb") as tempfile:
        tempfile.write(obj.file.read())

    is_text_detected = False
    is_nsfw = False
    face_not_detected = False

    if is_feature_enabled(USER_NSFW_DETECTION_FEATURE):
        is_nsfw = n2.predict_image(tempfile_name) > 0.5

    if is_feature_enabled(USER_FACE_DETECTION_FEATURE):
        face_not_detected = not(detect_face(tempfile_name))

    if is_feature_enabled(USER_TEXT_DETECTION_FEATURE):
        is_text_detected = detect_text_in_image(tempfile_name)

    if not any([is_nsfw, face_not_detected, is_text_detected]):
        os.remove(tempfile_name)
        return

    if is_nsfw:
        message = "Naked Photos Are Not Allowed. YOUR PICTURE HAS BEEN SUBMITTED FOR REVIEW."
    elif face_not_detected:
        message = "Upload Image with your face. YOUR PICTURE HAS BEEN SUBMITTED FOR REVIEW."
    elif is_text_detected:
        message = "Text Detected! YOUR PICTURE HAS BEEN SUBMITTED FOR REVIEW."

    ReviewUserPhoto.objects.create(
        user_photo=obj,
        file=obj.file
    )

    if UserPhoto.objects.filter(user=obj.user).count() == 1:
        if obj.user.gender == 0:
            obj.file = (
                BlockedImageAlternatives.objects.filter(action="MALE")
                .last()
                .image
            )
        elif obj.user.gender == 1:
            obj.file = (
                BlockedImageAlternatives.objects.filter(action="FEMALE")
                .last()
                .image
            )
        else:
            obj.file = (
                BlockedImageAlternatives.objects.filter(action="PREFER_NOT_TO_SAY")
                .last()
                .image
            )
    else:
        obj.file = None

    obj.save()

    notification_obj = Notification(
        user=obj.user, notification_setting_id="USERPICDETECT", data={}
    )
    send_notification_fcm(notification_obj=notification_obj, message=message)
    os.remove(tempfile_name)


def all_user_multi_stories_query(info, stat=False):
    user = info.context.user
    story_together_limit = UserLimit.objects.get(
        action_name="MultiStoryLimit"
    ).limit_value
    results = []
    # find all stories within the storyvisible time
    try:
        visible_time = StoryVisibleTime.objects.all().first()
        hours = (
            visible_time.hours + visible_time.days * 24 + visible_time.weeks * 7 * 24
        )
    except:
        hours = 24

    visible_time_differ = datetime.datetime.now() - datetime.timedelta(hours=hours)
    stories = []

    if stat:
        stories = Story.objects.filter(is_published=False)
    else:
        stories = Story.objects.published().filter(
            Q(publish_at__gte=visible_time_differ) | Q(created_date__gte=visible_time_differ)
        )

    all_stories = (
        stories.exclude(user__blockedUsers__username=user.username)
        .order_by(F('publish_at').desc(nulls_last=True), '-created_date')
    )

    # fetch distinct users
    users_id = set(all_stories.values_list("user__id", flat=True))
    # creating story batch
    for user_id in users_id:
        all_user_stories = all_stories.filter(user__id=user_id)
        batch_number = all_user_stories.count() / story_together_limit
        batch_number = batch_number if batch_number.is_integer() else batch_number + 1

        # First Batch
        prepare_first_batch_stories = all_user_stories.count() % story_together_limit
        if prepare_first_batch_stories:
            story_batch = list(all_user_stories[:prepare_first_batch_stories])
            results.append(
                {
                    "user": all_user_stories[0].user,
                    "stories": Story.objects.filter(id__in=[i.id for i in story_batch]).order_by(F('publish_at').desc(nulls_last=True), '-created_date'),
                    "latest_time": all_user_stories[0].id,
                    "batch_number": batch_number,
                }
            )
            all_user_stories = all_user_stories.exclude(id__in=[i.id for i in story_batch])
            batch_number -= 1
        # Remaining Batch
        for i in range(0, all_user_stories.count(), story_together_limit):
            story_batch = list(all_user_stories[i : i + story_together_limit])
            results.append(
                {
                    "user": all_user_stories[0].user,
                    "stories": Story.objects.filter(id__in=[i.id for i in story_batch]).order_by(F('publish_at').desc(nulls_last=True), '-created_date'),
                    "latest_time": all_user_stories[0].id,
                    "batch_number": batch_number,
                }
            )
            batch_number -= 1
    # sorting
    return sorted(results, key=lambda x: x["latest_time"], reverse=True)

def replace_phone_number(text):
    # Detect phone numbers and replace it with ****
    total_numbers = re.findall("[0-9]", text)
    if len(total_numbers) > 9:
        for i in total_numbers:
            text = text.replace(i, "*")

    return text

def replace_domain_email(text):
    # Detect email and replace it with ****
    famous_domains = [
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "aol.com",
        "aim.com",
        "icloud.com",
        "protonmail.com",
        "pm.com",
        "zoho.com",
        "yandex.com",
        "gmx.com",
        "hubspot.com",
        "mail.com",
        "tutanota.com",
    ]
    tlds = ["com", "fr", "it", "ch", "sw", "us", "org", "net"]

    domains = []
    for domain in famous_domains:
        domain = domain.split(".")[0].strip()
        domains.extend([f"{domain}.{tld}" for tld in tlds])

    domains.append("titan.email")

    words = text.split(" ")
    for i in range(0, len(words)):
        if "@" in words[i]:
            if "@" == words[i][0]:
                words[i] = "*"
                words[i - 1] = "*" * len(words[i - 1])

                for j in range(i + 1, len(words)):
                    if "." in words[j] or any(x in words[j] for x in tlds):
                        words[j] = "*" * len(words[j])
                        break
                    else:
                        words[j] = "*" * len(words[j])
            else:
                words[i] = "*" * len(words[i])
        else:
            for domain in domains:
                if domain in words[i]:
                    if words[i][0 : len(domain)] == domain:
                        words[i - 1] = "*" * len(words[i - 1])
                    words[i] = "*" * len(words[i])

    text = " ".join(words)
    return text

def replace_url(text):
    pattern = re.compile(r'https?://\S+|www\.\S+|\b(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}\b')
    urls = re.findall(pattern, text)
    for url in urls:
        text = text.replace(url, '*' * len(url))

    return text

def modify_text(text):
    try:
        text = replace_phone_number(text)
        text = replace_domain_email(text)
        text = replace_url(text)
    except Exception as e:
        print(e)

    return text


def get_worker_user(request_user, moderator_id):
    if "CHATTER" in request_user.roles.all().values_list('role', flat=True) and moderator_id is not None:
        try:
            return User.objects.get(id=moderator_id)
        except User.DoesNotExist:
            return Exception(translate_error_message(request_user, "Invalid moderator_id"))
    return request_user

def user_has_valid_userphoto(user):
    user_roles = user.roles.all().values_list('role', flat=True)
    allowed_roles = ["CHATTER", "ADMIN", "MODERATOR"]
    if any(string in allowed_roles for string in user_roles):
        return True
    else:
        default_imgs = BlockedImageAlternatives.objects.all().values_list("image")
        return UserPhoto.objects.filter(
            user=user
        ).exclude(
            file__in=default_imgs
        ).exclude(file='').exists()
