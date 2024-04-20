from celery import shared_task
from django.core.files import File
from pathlib import Path
from django.core.files.storage import default_storage
from io import BytesIO
from .models import Story
import cv2
from django.core.files.base import ContentFile
import tempfile

@shared_task(name="clear_story")
def clean_story(*args, **kwargs):
    from moments.models import Story
    import datetime

    if args:
        hours = int(args[0])
    else:
        hours = 1
    timedelta = datetime.timedelta(hours)
    Story.objects.filter(created_date__gte=datetime.datetime.now() - timedelta).delete()

def create_thumbnail_urgent(id, new_story=None):
    story = Story.objects.get(id=id)
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(story.file.read())
        tmp_file.flush()
        vidcap = cv2.VideoCapture(tmp_file.name)
        success, image = vidcap.read()
        if success:
            _, img = cv2.imencode(".jpeg", image)
            img_bytes = BytesIO(img.tobytes())
            file = ContentFile(img_bytes.getvalue())
            file_name = "thumbnail.jpeg"
            new_story.thumbnail.save(file_name, file, save=True)


@shared_task
def createThumbnail(id):
    create_thumbnail_urgent(id)
    return


@shared_task
def broadcast_story_type(story_ids):
    from moments.schema import OnUpdateStory

    for story_id in story_ids:
        OnUpdateStory.broadcast(group=None, payload={"story_id": story_id})
        import time

        time.sleep(1)
    return
