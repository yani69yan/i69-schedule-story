from django import forms
from django.contrib import admin
from django.contrib.admin.options import ModelAdmin
from django.shortcuts import HttpResponseRedirect
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django_object_actions import DjangoObjectActions

from chat.models import Notification, send_notification_fcm
from moments.models import (Comment, GenericComment, GenericLike, Like, Moment,
                            Report, ReportComment, ReviewMoment, ReviewStory,
                            Story, StoryReport, StoryVisibleTime)
from moments.schema import NotifyNewMoment, OnNewStory


class AllMoment(Moment):
    class Meta:
        proxy = True
        verbose_name = 'Moment'
        verbose_name_plural = 'Moment'


@admin.register(AllMoment)
class MomentAdmin(admin.ModelAdmin):
    def image(self, obj):
        file = obj.file
        ext = file.name.split(".")[-1]

        if ext.lower() in ["jpg", "png", "jpeg"]:
            return format_html(
                '<img src="{}" width="auto" height="80px" />'.format(file.url)
            )
        else:
            return format_html(
                '<video src="{}" width="auto" height="80px" /></video?>'.format(
                    file.url
                )
            )

    list_display = ["user", "Title", "created_date", "image"]
    ordering = ("Title",)
    order_by = ["user", "Title", "created_date"]
    search_fields = ("Title", "user__username", "user__fullName", "user__email")
    readonly_fields = [
        "view_thumbnail",
    ]

    class Media:
        js = ("admin/js/admin_paginator.js",)

    def changelist_view(self, request, extra_context=None):
        request.GET = request.GET.copy()
        page_param = int(request.GET.pop("list_per_page", [25])[0])
        self.list_per_page = page_param
        return super(MomentAdmin, self).changelist_view(request, extra_context)

    def view_thumbnail(self, obj):
        output = []
        if obj.file:
            ext = obj.file.name.split(".")[-1]
            file_url = obj.file.url
            if ext.lower() in ["jpg", "png", "jpeg"]:
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


class ScheduledMoment(Moment):
    class Meta:
        proxy = True
        verbose_name = 'Moment Scheduled'
        verbose_name_plural = 'Moment Scheduled'

@admin.register(ScheduledMoment)
class SchduledMomentAdmin(MomentAdmin):
    def get_queryset(self, request):
        qs = Moment.objects.filter(is_published=False)
        return qs


class PublishedMoment(Moment):
    class Meta:
        proxy = True
        verbose_name = 'Moment Published'
        verbose_name_plural = 'Moment Published'

@admin.register(PublishedMoment)
class PublishedMomentAdmin(MomentAdmin):
    def get_queryset(self, request):
        qs = Moment.objects.filter(is_published=True)
        return qs

class AllStory(Story):
    class Meta:
        proxy = True
        verbose_name = 'Story'
        verbose_name_plural = 'Story'

@admin.register(AllStory)
class StoryAdmin(admin.ModelAdmin):
    def image(self, obj):
        file = obj.file
        ext = file.name.split(".")[-1]

        if ext.lower() in ["jpg", "png", "jpeg"]:
            return format_html(
                '<img src="{}" width="auto" height="80px" />'.format(file.url)
            )
        else:
            return format_html(
                '<video src="{}" width="auto" height="80px" /></video?>'.format(
                    file.url
                )
            )

    list_display = ["user", "created_date", "image"]
    ordering = ("-created_date",)
    order_by = ["user", "created_date"]
    search_fields = ["user__username", "user__fullName", "user__email"]
    readonly_fields = [
        "view_thumbnail",
    ]

    class Media:
        js = ("admin/js/admin_paginator.js",)
        verbose_name = 'Story'
        verbose_name_plural = 'Story'

    def view_thumbnail(self, obj):
        output = []
        if obj.file:
            ext = obj.file.name.split(".")[-1]
            file_url = obj.file.url
            if ext.lower() in ["jpg", "png", "jpeg"]:
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

    def changelist_view(self, request, extra_context=None):
        request.GET = request.GET.copy()
        page_param = int(request.GET.pop("list_per_page", [25])[0])
        self.list_per_page = page_param
        return super(StoryAdmin, self).changelist_view(request, extra_context)


class ReviewStoryAdmin(DjangoObjectActions, admin.ModelAdmin):
    def image(self, obj):
        file = obj.file
        ext = file.name.split(".")[-1]

        if ext.lower() in ["jpg", "png", "jpeg"]:
            return format_html(
                '<img src="{}" width="auto" height="80px" />'.format(file.url)
            )
        else:
            return format_html(
                '<video src="{}" width="auto" height="80px" /></video?>'.format(
                    file.url
                )
            )

    list_display = ["user", "created_date", "file_type", "image"]
    readonly_fields = [
        "view_thumbnail",
    ]
    search_fields = ["user__username", "user__fullName", "user__email"]

    class Media:
        js = ("admin/js/admin_paginator.js",)

    def changelist_view(self, request, extra_context=None):
        request.GET = request.GET.copy()
        page_param = int(request.GET.pop("list_per_page", [25])[0])
        self.list_per_page = page_param
        return super(ReviewStoryAdmin, self).changelist_view(request, extra_context)

    def view_thumbnail(self, obj):
        output = []
        if obj.file:
            file_url = obj.file.url
            if obj.file_type == "image":
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

    def approve_story(self, request, obj):
        new_story = Story.objects.create(
            user=obj.user, file=obj.file, thumbnail=obj.thumbnail
        )  # create story again
        notification_obj = Notification(
            user=obj.user,
            notification_setting_id="STREVIEW",
            data={},
        )  # create notification
        send_notification_fcm(
            notification_obj=notification_obj, status="approved"
        )  # send push notification
        OnNewStory.broadcast(
            group=None,
            payload={"user_id": str(obj.user.id), "story_id": new_story.id},
        )
        obj.delete()  # delete review object
        return HttpResponseRedirect("/admin/moments/reviewstory/")

    def reject_story(self, request, obj):
        notification_obj = Notification(
            user=obj.user,
            notification_setting_id="STREVIEW",
            data={},
        )  # create notification
        send_notification_fcm(
            notification_obj=notification_obj, status="rejected"
        )  # send push notification
        obj.delete()  # delete review object
        return HttpResponseRedirect("/admin/moments/reviewstory/")

    change_actions = ("approve_story", "reject_story")


class ScheduledStory(Story):
    class Meta:
        proxy = True
        verbose_name = 'Story Scheduled'
        verbose_name_plural = 'Story Scheduled'

@admin.register(ScheduledStory)
class SchduledStoryAdmin(StoryAdmin):
    def get_queryset(self, request):
        qs = Story.objects.filter(is_published=False)
        return qs


class PublishedStory(Story):
    class Meta:
        proxy = True
        verbose_name = 'Story Published'
        verbose_name_plural = 'Story Published'

@admin.register(PublishedStory)
class PublishedStoryAdmin(StoryAdmin):
    def get_queryset(self, request):
        qs = Story.objects.filter(is_published=True)
        return qs


class ReviewMomentAdmin(DjangoObjectActions, admin.ModelAdmin):
    def image(self, obj):
        file = obj.file
        ext = file.name.split(".")[-1]

        if ext.lower() in ["jpg", "png", "jpeg"]:
            return format_html(
                '<img src="{}" width="auto" height="80px" />'.format(file.url)
            )
        else:
            return format_html(
                '<video src="{}" width="auto" height="80px" /></video?>'.format(
                    file.url
                )
            )

    list_display = ["user", "image", "created_date", "file_type", "title"]
    readonly_fields = [
        "view_thumbnail",
    ]
    search_fields = ["title", "user__username", "user__fullName", "user__email"]

    class Media:
        js = ("admin/js/admin_paginator.js",)

    def changelist_view(self, request, extra_context=None):
        request.GET = request.GET.copy()
        page_param = int(request.GET.pop("list_per_page", [25])[0])
        self.list_per_page = page_param
        return super(ReviewMomentAdmin, self).changelist_view(request, extra_context)

    def view_thumbnail(self, obj):
        output = []
        if obj.file:
            file_url = obj.file.url
            if obj.file_type == "image":
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

    def approve_moment(self, request, obj):
        new_moment = Moment.objects.create(
            user=obj.user,
            file=obj.file,
            Title=obj.title,
            moment_description=obj.moment_description,
        )  # create story again
        notification_obj = Notification(
            user=obj.user,
            notification_setting_id="MMREVIEW",
            data={},
        )  # create notification
        send_notification_fcm(
            notification_obj=notification_obj, status="approved"
        )  # send push notification
        NotifyNewMoment.broadcast(payload=new_moment, group="moments")
        obj.delete()  # delete review object
        return HttpResponseRedirect("/admin/moments/reviewmoment/")

    def reject_moment(self, request, obj):
        notification_obj = Notification(
            user=obj.user,
            notification_setting_id="MMREVIEW",
            data={},
        )  # create notification
        send_notification_fcm(
            notification_obj=notification_obj, status="rejected"
        )  # send push notification
        obj.delete()  # delete review object
        return HttpResponseRedirect("/admin/moments/reviewmoment/")

    change_actions = ("approve_moment", "reject_moment")


class ReviewCommentAdmin(ModelAdmin):
    list_display = ("id", "user", "created_at")
    list_select_related = ('user', 'momemt', 'reply_to')
    search_fields = (
        'id',
        'user__id',
        'user__fullName',
        'user__first_name',
        'user__last_name',
        'user__username',
        'user__email',
    )
    class Media:
        js = ("admin/js/admin_paginator.js",)

    def changelist_view(self, request, extra_context=None):
        request.GET = request.GET.copy()
        page_param = int(request.GET.pop("list_per_page", [25])[0])
        self.list_per_page = page_param
        return super(ReviewCommentAdmin, self).changelist_view(request, extra_context)


class ReviewLikeAdmin(ModelAdmin):
    list_display = ("id", "user", "created_at")
    class Media:
        js = ("admin/js/admin_paginator.js",)

    def changelist_view(self, request, extra_context=None):
        request.GET = request.GET.copy()
        page_param = int(request.GET.pop("list_per_page", [25])[0])
        self.list_per_page = page_param
        return super(ReviewLikeAdmin, self).changelist_view(request, extra_context)


class ReviewGenericLikeAdmin(ModelAdmin):
    class Media:
        js = ("admin/js/admin_paginator.js",)

    def changelist_view(self, request, extra_context=None):
        request.GET = request.GET.copy()
        page_param = int(request.GET.pop("list_per_page", [25])[0])
        self.list_per_page = page_param
        return super(ReviewGenericLikeAdmin, self).changelist_view(
            request, extra_context
        )

class StoryReportAdmin(ModelAdmin):
    model = StoryReport
    readonly_fields = ['story_owner', 'reported_by', 'Report_msg', 'story_image', 'timestamp']
    exclude = ("story", "user")
    list_display = ['story_owner', 'reported_by', 'modified_report_msg', 'story_image', 'timestamp']
    list_select_related = ('user', 'story')
    search_fields = (
        'id',
        'user__id',
        'user__fullName',
        'user__first_name',
        'user__username',
        'user__last_name',
        'user__email',
        'story__user__id',
        'story__user__fullName',
        'story__user__username',
        'story__user__first_name',
        'story__user__last_name',
        'story__user__email',
    )

    def reported_by(self, obj):
        return StoryReport.objects.get(id=obj.id).user.username

    def story_owner(self, obj):
        return StoryReport.objects.get(id=obj.id).story.user.username

    def modified_report_msg(self, obj):
        output = []
        msg = obj.Report_msg
        if msg:
            output.append(

                '<p style="max-width: 300px; max-height: 300px; word-wrap: break-word;" />'
                '<span>%s'
                    % (msg)
            )
        return mark_safe("".join(output))

    def story_image(self, obj):
        output = []
        file = obj.story.file
        if obj.story.file:
            ext = file.name.split(".")[-1]
            file_url = file.url
            if ext.lower() in ["jpg", "png", "jpeg"]:
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


class ReportCommentAdmin(ModelAdmin):
    model = ReportComment
    readonly_fields = ['comment_owner', 'reported_by', 'Report_msg', 'timestamp']
    exclude = ("story", "user")
    list_display = ['comment_owner', 'reported_by', 'modified_report_msg', 'timestamp']
    list_select_related = (
        'user',
        'comment',
        'comment__user'
    )
    search_fields = (
        'user__id',
        'user__fullName',
        'user__first_name',
        'user__username',
        'user__last_name',
        'user__email',
        'comment__user__id',
        'comment__user__fullName',
        'comment__user__username',
        'comment__user__first_name',
        'comment__user__last_name',
        'comment__user__email',
    )

    def reported_by(self, obj):
        return ReportComment.objects.get(id=obj.id).user.username

    def comment_owner(self, obj):
        return ReportComment.objects.get(id=obj.id).comment.user.username

    def modified_report_msg(self, obj):
        output = []
        msg = obj.Report_msg
        if msg:
            output.append(

                '<p style="max-width: 300px; max-height: 300px; word-wrap: break-word;" />'
                '<span>%s'
                % (msg)
            )
        return mark_safe("".join(output))

class ReportMoment(Report):
    class Meta:
        proxy = True
        verbose_name = 'Report Moments'
        verbose_name_plural = 'Report Moments'

@admin.register(ReportMoment)
class ReportAdmin(ModelAdmin):
    model = Report
    readonly_fields = ['momemt_owner', 'reported_by', 'Report_msg', 'moment_image']
    exclude = ("story", "user")
    list_display = ['momemt_owner', 'reported_by', 'modified_report_msg', 'moment_image']

    def reported_by(self, obj):
        return Report.objects.get(id=obj.id).user.username

    def momemt_owner(self, obj):
        return Report.objects.get(id=obj.id).momemt.user.username

    def modified_report_msg(self, obj):
        output = []
        msg = obj.Report_msg
        if msg:
            output.append(

                '<p style="max-width: 300px; max-height: 300px; word-wrap: break-word;" />'
                '<span>%s'
                    % (msg)
            )
        return mark_safe("".join(output))

    def moment_image(self, obj):
        output = []
        file = obj.momemt.file
        if obj.momemt.file:
            ext = file.name.split(".")[-1]
            file_url = file.url
            if ext.lower() in ["jpg", "png", "jpeg"]:
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


class StoryVisibleAdminForm(forms.ModelForm):
    class Meta:
        model = StoryVisibleTime
        fields = (
            "weeks",
            "days",
            "hours",
        )


@admin.register(StoryVisibleTime)
class StoryVisibleAdmin(ModelAdmin):
    list_display = ["text", "weeks", "days", "hours"]

    form = StoryVisibleAdminForm

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Comment, ReviewCommentAdmin)
admin.site.register(Like, ReviewLikeAdmin)
admin.site.register(StoryReport, StoryReportAdmin)
admin.site.register(GenericLike, ReviewGenericLikeAdmin)
admin.site.register(GenericComment)
admin.site.register(ReviewStory, ReviewStoryAdmin)
admin.site.register(ReviewMoment, ReviewMomentAdmin)
admin.site.register(ReportComment, ReportCommentAdmin)
