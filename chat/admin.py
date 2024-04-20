from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from chat.models import (Broadcast, ChatMessageImages, ContactUs,
                         DeletedMessage, DeletedMessageDate, FirstMessage,
                         FreeMessageLimit, Message, Notes, Notification,
                         NotificationSettings, Room)


class PaginatedBaseAdmin(admin.ModelAdmin):

    class Media:
        js = ("admin/js/admin_paginator.js",)

    def changelist_view(self, request, extra_context=None):
        request.GET = request.GET.copy()
        page_param = int(request.GET.pop("list_per_page", [25])[0])
        self.list_per_page = page_param
        return super(PaginatedBaseAdmin, self).changelist_view(request, extra_context)


class CustomRoomAdmin(PaginatedBaseAdmin):
    list_display = ("id", "name", "user_from", "user_to", )
    list_select_related = ['user_id', 'target', ]
    ordering = ("-id", )
    list_filter = ("name", )
    search_fields = (
        "name",
        "user_id__username",
        "user_id__fullName",
        "user_id__email",
        "target__username",
        "target__fullName",
        "target__email",
    )

    def user_from(self, obj):
        return obj.user_id

    def user_to(self, obj):
        return obj.target


class BaseMessageAdmin(PaginatedBaseAdmin):
    list_display = ["id", "room_id", "user_id", "timestamp", "content", "read", ]
    list_select_related = ['room_id', 'room_id__user_id', 'room_id__target', ]
    ordering = ("-timestamp", )
    list_filter = ("room_id", )
    search_fields = (
        "content",
        "room_id__user_id__fullName",
        "room_id__target__fullName",
    )

    restricted_msgs = False

    def room_id(self, obj):
        return Room.objects.get(obj.room_id).name

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.filter(restricted_msg=self.restricted_msgs)
        return queryset


class RestrictedMessages(Message):
    class Meta:
        proxy = True
        verbose_name = "_Messages For Restricted User"
        verbose_name_plural = "_Messages For Restricted Users"


@admin.register(RestrictedMessages)
class RestrictedMessagesAdmin(BaseMessageAdmin):
    list_display = (
        "id", "room_id", "user_id", "timestamp",
        "content", "read", "restricted_msg",
    )

    restricted_msgs = True


class CustomBroadcastAdmin(PaginatedBaseAdmin):
    list_display = ("id", "by_user_id", "content", "timestamp", )
    list_select_related = ['by_user_id', ]
    ordering = ("-timestamp", )
    search_fields = ("id", "by_user_id__fullName", "by_user_id__username", )


class CustomFirstMessageAdmin(PaginatedBaseAdmin):
    list_display = ("id", "by_user_id", "content", "timestamp", )
    list_select_related = ['by_user_id', ]
    ordering = ("-timestamp", )
    search_fields = ("by_user_id", )


class NotificationsAdmin(PaginatedBaseAdmin):
    list_display = (
        "id",
        "user",
        "created_date",
        "sender",
        "seen",
        "notification_setting",
        "notification_body",
        "data",
    )
    list_select_related = ['user', 'notification_setting', ]
    ordering = ("-created_date", )
    search_fields = (
        "user__username", "user__email",
        "notification_setting__id",
    )
    list_filter = (
        "notification_setting__id",
        "seen",
    )


class MessageInline(admin.TabularInline):
    model = Message
    fields = ["content", "user_id", "read"]
    readonly_fields = ["content", "user_id", "read"]
    can_delete = False
    show_change_link = False
    extra = 0

    def has_add_permission(self, request, obj):
        return False

    class Media:
        js = ("admin/js/admin_paginator.js",)

    def changelist_view(self, request, extra_context=None):
        request.GET = request.GET.copy()
        page_param = int(request.GET.pop("list_per_page", [25])[0])
        self.list_per_page = page_param
        return super(MessageInline, self).changelist_view(request, extra_context)


class Chats(Room):
    class Meta:
        proxy = True
        verbose_name = "Chat"
        verbose_name_plural = "Chats"


class ChatAdmin(PaginatedBaseAdmin):
    inlines = [
        MessageInline,
    ]
    list_display = ["name", "user_id", "target", "timestamp", ]
    list_select_related = ['user_id', 'target', ]
    readonly_fields = ["target", "user_id", "name", "last_modified", "deleted", "timestamp", ]
    search_fields = (
        "name",
        "user_id__username",
        "user_id__email",
        "user_id__fullName",
        "target__username",
        "target__email",
        "target__fullName",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CustomDeletedMessages(PaginatedBaseAdmin):
    list_display = (
        "id", "room_id", "user_id",
        "timestamp", "deleted_timestamp",
    )
    list_select_related = ['room_id', 'user_id', ]
    search_fields = (
        "room_id__name",
        "user_id__username",
        "user_id__email",
        "user_id__fullName",
    )
    list_per_page = 25


class CustomNotificationSettings(PaginatedBaseAdmin):
    list_display = ("id", "title", "message_str", "title_fr", )
    search_fields = ("id", "title", "message_str", "title_fr", )


class CustomChatMessageImages(PaginatedBaseAdmin):

    list_display = ["upload_type", "image_file", "timestamp"]
    readonly_fields = [
        "view_thumbnail",
        "timestamp"
    ]

    def image_file(self, obj):
        file = obj.image
        ext = file.name.split(".")[-1]
        img_html_t = '<img src="/media/{}" width="auto" height="80px" />'
        vid_html_t = '<video src="/media/{}" width="auto" height="80px" /></video?>'

        return format_html(
            img_html_t.format(file)
        ) if ext.lower() in ["jpg", "png", "jpeg"] else format_html(
            vid_html_t.format(file)
        )

    def view_thumbnail(self, obj):
        output = []
        if not obj.image:
            return mark_safe("".join(output))

        file_url = obj.image.url
        if obj.upload_type == "image":
            output.append(
                '<a href="javascript:;" class="mtooltip left">'
                '<img src="%s" alt="" style="max-width: 300px; max-height: 300px;" />'
                '<span><img src="%s" style="max-width: 300px; max-height: 300px;"/></span>'
                "</a>" % (file_url, file_url)
            )
        else:
            output.append(
                '<a href="javascript:;" class="mtooltip left">'
                '<video width="600" height="600" controls>'
                '<source src="%s" type="video/%s">'
                "</video>"
                "</a>" % (file_url, file_url.split("/")[-1].split(".")[-1])
            )

        style_css = """
        <style>
        a.mtooltip { outline: none; cursor: help; text-decoration: none; position: relative;}
        a.mtooltip span {margin-left: -999em; padding:5px 6px; position: absolute; width:auto; white-space:nowrap; line-height:1.5;box-shadow:0px 0px 10px #999; -moz-box-shadow:0px 0px 10px #999; -webkit-box-shadow:0px 0px 10px #999; border-radius:3px 3px 3px 3px; -moz-border-radius:3px; -webkit-border-radius:3px;}
        a.mtooltip span img {max-width:300px;}
        a.mtooltip {background:#ffffff; text-decoration:none;cursor: help;} /*BG color is a must for IE6*/
        a.mtooltip:hover span{ left: 1em;top: 0em; margin-left: 0; z-index:99999; position:absolute; background:#ffffff; border:1px solid #cccccc; color:#6c6c6c;}

        #changelist-form .results{overflow-x: initial!important;}
        </style>
        """
        output.append(style_css)
        return mark_safe("".join(output))


class FreeMessageLimitAdmin(admin.ModelAdmin):
    list_display = ["user"]

    def has_add_permission(self, request):
        if self.model.objects.count() >= 1:
            return False

        return super().has_add_permission(request)


class ContactUsAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at", "message")
    search_fields = ["name", "email"]


admin.site.register(Chats, ChatAdmin)
admin.site.register(Message, BaseMessageAdmin)
admin.site.register(Room, CustomRoomAdmin)
admin.site.register(Broadcast, CustomBroadcastAdmin)
admin.site.register(FirstMessage, CustomFirstMessageAdmin)
admin.site.register(ChatMessageImages, CustomChatMessageImages)
admin.site.register(NotificationSettings, CustomNotificationSettings)
admin.site.register(Notification, NotificationsAdmin)
admin.site.register(DeletedMessage, CustomDeletedMessages)
admin.site.register(DeletedMessageDate)
admin.site.register(Notes, PaginatedBaseAdmin)
admin.site.register(FreeMessageLimit, FreeMessageLimitAdmin)
admin.site.register(ContactUs, ContactUsAdmin)
