import traceback
from datetime import timedelta

from celery import shared_task
from django.db.models import Count, Q
from django.utils import timezone

from chat.models import (DeletedMessage, DeletedMessageDate, Message,
                         Notification, send_notification_fcm)
from user.models import (ChatsQue, ChatsQueSetting, DeleteAccountSetting,
                         ModeratorOnlineScheduler, Settings, User, UserRole)
from user.utils import notifiy_near_by_users


@shared_task(name="delete_old_deleted_messages")
def delete_old_deleted_messages(*args, **kwargs):
    no_of_days = DeletedMessageDate.objects.last().no_of_days
    DeletedMessage.objects.filter(
        deleted_timestamp__lte=timezone.now() - timedelta(days=7)
    )
    # print(f"MESSAGE DELETED OLDER THAN {no_of_days} Days")


def _get_chat_queue_setting(task_name, default=1):
    try:
        setting = ChatsQueSetting.objects.filter(taskName=task_name).first()
        if not setting:
            return default
        time_map = {"Days": 86400, "Hours": 3600, "Minutes": 60, "Seconds": 1}
        value = setting.numberOfPeriods * time_map.get(setting.intervalPeriod)
        return value
    except Exception:
        return default


def _get_allow_offline_mods_to_assign_worker():
    default = False
    try:
        settings = ChatsQueSetting.objects.filter(
            taskName="unassign_chat_from_inactive_worker_to_active_worker_intervel"
        ).first()
        # print(getattr(settings, 'allow_offline_mods', False))
        if settings and getattr(settings, 'allow_offline_mods', False):
            default = settings.allow_offline_mods
            # print(f"=========================== Allow Offline Mods to Assign Worker:{default}")
    except Exception as e:
        pass
        # print(f"==================== Error: {e}")
    return default


def _logout_worker(worker):
    try:
        user_token = None
        try:
            user_token = worker.auth_token
        except:
            pass
            # print("No auth token")
        if user_token:
            try:
                worker.auth_token.delete()
                # print("Logging out worker.")
            except:
                pass
                # print("Token already deleted.")
        worker.isOnline = False
        worker.fake_users.clear()
        worker.save()
        print("Logging out worker with moderator user removed.")
    except Exception as e:
        pass
        # print(e, "Failed to logout user")


@shared_task(name="chats_queue_scheduler_task")
def chats_queue_scheduler_task(*args, **kwargs):

    queue_chats = ChatsQue.objects.all().order_by("date_created")
    # print(f"Chats in Queue {queue_chats.count()}")

    allow_offline_mod_assignment = _get_allow_offline_mods_to_assign_worker()
    for chat in queue_chats:
        # Check the configuration
        if not allow_offline_mod_assignment and not chat.moderator.isOnline:
            # print(f"========================= {chat.moderator.id} is_online: {chat.moderator.isOnline}")
            if chat.isAssigned:
                # print("========================= As Moderator is offline, Un-assign Chat")
                # Remove the chat assignment
                chat.moderator.owned_by.remove(chat.worker)
                chat.worker = None
                chat.isAssigned = False
                chat.save()
            # print("========================= Moderator is offline we will not assign the worker to chat.")
            continue

        messages = Message.objects.filter(room_id=chat.room_id, restricted_msg=False).order_by("-timestamp")
        if not chat.isAssigned:
            for msg in messages:
                if msg.user_id.roles.filter(role__in=["MODERATOR"]):
                    break
                msg.read = None
                msg.save()

        if chat.isAssigned:
            if not chat.worker.isOnline:
                chat.moderator.owned_by.remove(chat.worker)
                chat.worker = None
                chat.isAssigned = False
                chat.save()

            time_from_db = _get_chat_queue_setting(
                task_name=ChatsQueSetting.CHAT_SHIFT_INTERVAL,
                default=1,
            )

            unassigne_in_active_interval = timezone.now() - timezone.timedelta(
                seconds=time_from_db
            )

            # print(f"Un Assigned Worker Time setting value {time_from_db} seconds")

            if chat.updated_at < unassigne_in_active_interval:
                available_workers = (
                    User.objects.filter(roles__role__in=["CHATTER"], isOnline=True)
                    .annotate(fake_count=Count("fake_users"))
                    .filter(fake_count__lt=1)
                )
                worker = None
                if available_workers.count() > 0:
                    worker = available_workers[0]
                if worker:
                    for msg in messages:
                        if msg.user_id.roles.filter(role__in=["MODERATOR"]):
                            break
                        msg.read = None
                        msg.save()
                    # print(
                        # "chat remove from worker and assign to other free online worker"
                    # )
                    chat.moderator.owned_by.remove(chat.worker)
                    chat.moderator.owned_by.add(worker)
                    chat.worker = worker
                    chat.save()
                    # print(f"assigning {chat.moderator} to ", worker)
                else:
                    # print(f"Un Assigned Time is passed but no available worker")
                    chat.moderator.owned_by.remove(chat.worker)
                    chat.worker = None
                    chat.isAssigned = False
                    chat.save()
        else:
            available_workers = (
                User.objects.filter(roles__role__in=["CHATTER"], isOnline=True)
                .annotate(fake_count=Count("fake_users"))
                .filter(fake_count__lt=1)
            )

            if available_workers.count() > 0:
                chat.worker = available_workers[0]
                chat.isAssigned = True
                chat.save()
                available_workers[0].fake_users.add(chat.moderator)
                try:
                    last_message = Message.objects.filter(room_id__id=chat.room_id, restricted_msg=False).order_by("-timestamp").first()
                    if last_message:
                        last_message.receiver_worker = chat.worker
                        last_message.save()
                except:
                    pass
                #print("chat assign to worker")

    logout_intervl_db = _get_chat_queue_setting(
        task_name=ChatsQueSetting.INACTIVE_WORKER_LOGOUT_INTERVAL, default=1
    )

    #print(f"Logout In Active worker interval: {logout_intervl_db} seconds")

    online_workers = User.objects.filter(roles__role__in=["CHATTER"], isOnline=True)
    busy_workers = (
        User.objects.filter(roles__role__in=["CHATTER"], isOnline=True)
        .annotate(fake_count=Count("fake_users"))
        .filter(fake_count__gt=0)
    )
    # print(f"Busy workers {busy_workers}")
    # print(f"Online Workers: {online_workers}")

    for online_worker in online_workers:
        logout_intervl = timezone.now() - timezone.timedelta(seconds=logout_intervl_db)
        # print(f"User Last seen {online_worker.user_last_seen} : Logout Date: {logout_intervl}")
        if online_worker.user_last_seen == None:
            _logout_worker(worker=online_worker)
        else:
            if online_worker.user_last_seen < logout_intervl:
                # print("LoggingOut the Worker")
                _logout_worker(worker=online_worker)

    moderator_lists = ModeratorOnlineScheduler.objects.all()
    time = timezone.now().time()
    for list in moderator_lists:
        moderator_list = list.moderator_list.all()
        for moderator in moderator_list:
            if time > list.online_time and time < list.offline_time:
                if not moderator.isOnline:
                    moderator.isOnline = True
                    moderator.save()
            else:
                if moderator.isOnline:
                    moderator.isOnline = False
                    moderator.save()


@shared_task(name="unassign_moderator_from_inactive_workers")
def unassign_moderator_from_inactive_workers(*args, **kwargs):
    pass


@shared_task(name="assign_moderator_from_inactive_to_active_workers")
def assign_moderator_from_inactive_to_active_workers(*args, **kwargs):
    pass


def recently_notified_user_ids():
    notification_setting = "MSGREMINDER"
    timedelta_10_min = timezone.now() - timezone.timedelta(minutes=10)
    notified_users = list(
        Notification.objects.select_related("user")
        .filter(
            created_date__gt=timedelta_10_min,
            notification_setting__id=notification_setting,
        )
        .distinct("user")
        .values_list("user__id", flat=True)
    )
    return notified_users


@shared_task(name="reminder_for_unread_messages")
def reminder_for_unread_messages(*args, **kwargs):
    messages = Message.objects.select_related("room_id").filter(read__isnull=True)
    already_notified_users = recently_notified_user_ids()
    # Calculate all unread messages for user from all the rooms
    for message in messages:
        room = message.room_id
        reciever = None
        if room.user_id == message.user_id:
            reciever = room.target
        else:
            reciever = room.user_id
        if reciever.id in already_notified_users:
            continue
        already_notified_users.append(reciever.id)
        unread_messasge_count = (
            Message.objects.filter(
                Q(Q(room_id__user_id=reciever) | Q(room_id__target_id=reciever))
                & Q(read__isnull=True)
            )
            .exclude(user_id=reciever)
            .count()
        )
        send_notification(reciever.id, unread_messasge_count)


def send_notification(user_id, unread_message_count):
    notification_setting = "MSGREMINDER"
    data = {
        "notification_type": notification_setting,
    }
    notification_obj = Notification(
        user_id=user_id,
        notification_setting_id=notification_setting,
        data=data
    )
    send_notification_fcm(
        notification_obj=notification_obj,
        message_count=f"You have {unread_message_count} unread messages",
    )


@shared_task(name="send_notification_to_nearby_users")
def send_notification_to_nearby_users(user_id):
    try:
        distance_km = Settings.get_setting(
            key="notify_new_user_radius_km", default=50000
        )
        notifiy_near_by_users(user_id=user_id, distance_km=distance_km)
    except Exception as e:
        pass
        # print(traceback.print_exc(), e)
        # print(f"Failed to send Notification")


@shared_task(name="delete_user_data_after_retention")
def delete_user_data_after_retention(*args, **kwargs):
    retain_data_for_days_model = DeleteAccountSetting.objects.last()
    retain_data_for_days = 0
    if retain_data_for_days_model:
        retain_data_for_days = retain_data_for_days_model.retain_data_for_days
    retain_data_for_days = retain_data_for_days or 90
    to_delete = User.objects.filter(
        is_deleted=True, user_deleted_at__lte=timezone.now() - timedelta(days=retain_data_for_days)
    ).all()
    # It is required to individually delete the user to delete the all related data
    # print("++++++++++++++++++++++++++++++++++Deleting Users:")
    for delete_ in to_delete:
        # print(f"++++++++++++++++++++++++++++++++++Deleting User:{delete_.id}")
        delete_.delete()
        # print(f"++++++++++++++++++++++++++++++++++Deleted User:{delete_.id}")

    # print(f"DELETED USERS DELETED AFTER RETENTION PERIOD {retain_data_for_days} Days")


def _logout_admin(admin):
    try:
        admin.auth_token.delete()
    except:
        pass

    admin.isOnline = False
    admin.save()


@shared_task(name="logout_inactive_admins")
def logout_inactive_admins(*args, **kwargs):
    inactive_admin_logout_interval = _get_chat_queue_setting(
        ChatsQueSetting.INACTIVE_ADMIN_LOGOUT_INTERVAL,
        default=1800
    )

    admins = User.objects.filter(
        roles__in=UserRole.objects.filter(role=UserRole.ROLE_ADMIN),
        isOnline=True
    )
    for admin in admins:
        logout_interval = timezone.now() - timezone.timedelta(seconds=inactive_admin_logout_interval)
        if not admin.user_last_seen or admin.user_last_seen < logout_interval:
            _logout_admin(admin)
