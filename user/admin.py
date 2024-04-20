import json

import requests
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.options import IS_POPUP_VAR, ModelAdmin
from django.contrib.admin.utils import unquote
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.db import router, transaction
from django.db.models import Count, F, Q
from django.db.models.aggregates import Max
from django.forms.widgets import ClearableFileInput
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django_object_actions import DjangoObjectActions
from django_otp.plugins.otp_static.admin import StaticTokenInline
from django_otp.plugins.otp_static.models import StaticDevice
from easy_select2 import Select2, select2_modelform
from import_export.admin import ExportActionMixin, ImportExportModelAdmin

from chat.admin import PaginatedBaseAdmin
from chat.models import Message, Notification, Room, send_notification_fcm
from gifts.models import Giftpurchase
from purchase.models import Purchase
from purchase.utils import payment_method_choices
from user.BothFiltersm2mWidget import FilteredSelectMultipleM2M
from user.constants import PIC_REVIEW_NOTIFICATION_SETTING
from user.forms import CoinSettingsRegionForm, UserInterestedInRegionForm
from user.models import (BlockedImageAlternatives, ChatsQue, ChatsQueSetting,
                         CoinSettings, CoinSettingsForRegion,
                         CoinSettingsRegion, CoinsHistory, CoinSpendingHistory,
                         Country, DeleteAccountSetting,
                         ErrorMessageTranslation, FailedFCMMessage,
                         FeatureSettings, InstagramScrapy,
                         ModeratorOnlineScheduler, PrivatePhotoViewRequest,
                         PrivatePhotoViewTime, PrivateUserPhoto, ProfileFollow,
                         ProfileVisit, ReviewUserPhoto, SetInterestedInRegion,
                         Settings, User, UserForModsRestriction,
                         UserInterestedIn, UserInterestForRegion, UserLimit,
                         UserPhoto, UserProfileTranlations, UserRole,
                         UserSocialProfile)
from worker.models import WorkerInvitation

csrf_protect_m = method_decorator(csrf_protect)
sensitive_post_parameters_m = method_decorator(sensitive_post_parameters())

admin.site.unregister(StaticDevice)


class InstagramAdmin(admin.ModelAdmin):

    def get_urls(self):
        urls = super().get_urls()
        new_urls = [path('scrape-insta/', self.scrapeInsta, name='scrape-insta')]
        return new_urls + urls

    def scrapeInsta(self, request):
        if request.method == 'POST':
            user = request.POST.get('name')
            if not user:
                return redirect('/admin/user/instagramscrapy/')

            response = requests.get(f'http://138.201.88.162:8080/scrape/{user}')
            if response.status_code == 200:
                data = json.loads(response.text)
                user_data = data[0]
                followers = user_data['followers']
                following = user_data['following']
                full_name = user_data['full_name']
                posts_count = user_data['posts']
                post_data = user_data['posts_data']
                profile_picture = user_data['profile_picture']

                InstagramScrapy.objects.create(
                    username=user,
                    followers=followers,
                    following=following,
                    full_name=full_name,
                    total_posts=posts_count,
                    posts_data=post_data,
                    profile_picture=profile_picture
                )

        return redirect('/admin/user/instagramscrapy/')


class CoinPurchaseFilter(SimpleListFilter):
    title = "Purchased coins"
    parameter_name = "purchased_coins"

    def lookups(self, request, model_admin):
        return [("Yes", "Yes"), ("No", "No")]

    def queryset(self, request, queryset):
        if self.value() == "Yes":
            return queryset.exclude(purchase_coins_date=None)
        if self.value() == "No":
            return queryset.filter(purchase_coins_date=None)
        return queryset


class UserOnlineFilter(SimpleListFilter):
    """This filter is for admin to filter all the users based on their
    online state.
    """

    title = "User Online Filter"
    parameter_name = "user_online_filter"

    def lookups(self, request, model_admin):
        return [("Online", "Online"), ("Offline", "Offline")]

    def queryset(self, request, queryset):
        if self.value() == "Online":
            online_id_list = [query.id for query in queryset if query.isOnline]
            queryset = queryset.filter(id__in=online_id_list)
        if self.value() == "Offline":
            offline_id_list = [query.id for query in queryset if not query.isOnline]
            queryset = queryset.filter(id__in=offline_id_list)

        return queryset


class IsDeletedFilter(SimpleListFilter):
    title = "Is Deleted"  # or use _('country') for translated title
    parameter_name = "is_deleted"

    def lookups(self, request, model_admin):
        return [("Yes", "Yes"), ("No", "No")]

    def queryset(self, request, queryset):
        if self.value() == "Yes":
            return queryset.exclude(user_deleted_at=None)
        if self.value() == "No":
            return queryset.filter(user_deleted_at=None)
        return queryset


class IsDeletedFilterFilter(SimpleListFilter):
    title = "Is Deleted From"
    parameter_name = "is_deleted_from"

    def lookups(self, request, model_admin):
        return [
            ("30min-1h", "30min-1h"),
            ("1h-5h", "1h-5h"),
            ("5h-24h", "5h-24h"),
            ("24h-3d", "24h-3d"),
            ("3d-10d", "3d-10d"),
            ("10d-1m", "10d-1m"),
            ("more than 1m", "more than 1m"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "30min-1h":
            time_delta_30min = timezone.now() - timezone.timedelta(minutes=30)
            time_delta_1h = timezone.now() - timezone.timedelta(hours=1)
            return queryset.filter(
                user_deleted_at__lt=time_delta_30min, user_deleted_at__gt=time_delta_1h
            )

        if self.value() == "1h-5h":
            time_delta_1h = timezone.now() - timezone.timedelta(hours=1)
            time_delta_5h = timezone.now() - timezone.timedelta(hours=5)
            return queryset.filter(
                user_deleted_at__lt=time_delta_1h, user_deleted_at__gt=time_delta_5h
            )

        if self.value() == "5h-24h":
            time_delta_5h = timezone.now() - timezone.timedelta(hours=5)
            time_delta_24h = timezone.now() - timezone.timedelta(hours=24)
            return queryset.filter(
                user_deleted_at__lt=time_delta_5h, user_deleted_at__gt=time_delta_24h
            )

        if self.value() == "24h-3d":
            time_delta_24h = timezone.now() - timezone.timedelta(hours=24)
            time_delta_3d = timezone.now() - timezone.timedelta(days=3)
            return queryset.filter(
                user_deleted_at__lt=time_delta_24h, user_deleted_at__gt=time_delta_3d
            )

        if self.value() == "3d-10d":
            time_delta_3d = timezone.now() - timezone.timedelta(days=3)
            time_delta_10d = timezone.now() - timezone.timedelta(days=10)
            return queryset.filter(
                user_deleted_at__lt=time_delta_3d, user_deleted_at__gt=time_delta_10d
            )

        if self.value() == "10d-1m":
            time_delta_10d = timezone.now() - timezone.timedelta(days=10)
            time_delta_1m = timezone.now() - timezone.timedelta(days=30)
            return queryset.filter(
                user_deleted_at__lt=time_delta_10d, user_deleted_at__gt=time_delta_1m
            )

        if self.value() == "more than 1m":
            time_delta_1m = timezone.now() - timezone.timedelta(days=30)
            return queryset.filter(user_deleted_at__lt=time_delta_1m)

        return queryset


class RealUser(User):
    class Meta:
        proxy = True
        verbose_name = "_Real User"
        verbose_name_plural = "_Real Users"


class InactiveFromFilter(SimpleListFilter):
    title = "Inactive From"
    parameter_name = "inactive_from"

    def lookups(self, request, model_admin):
        return [
            ("30min-1h", "30min-1h"),
            ("1h-5h", "1h-5h"),
            ("5h-24h", "5h-24h"),
            ("24h-3d", "24h-3d"),
            ("3d-10d", "3d-10d"),
            ("10d-1m", "10d-1m"),
            ("more than 1m", "more than 1m"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "30min-1h":
            time_delta_30min = timezone.now() - timezone.timedelta(minutes=30)
            time_delta_1h = timezone.now() - timezone.timedelta(hours=1)
            return queryset.filter(
                last_login__lt=time_delta_30min, last_login__gt=time_delta_1h
            )

        if self.value() == "1h-5h":
            time_delta_1h = timezone.now() - timezone.timedelta(hours=1)
            time_delta_5h = timezone.now() - timezone.timedelta(hours=5)
            return queryset.filter(
                last_login__lt=time_delta_1h, last_login__gt=time_delta_5h
            )

        if self.value() == "5h-24h":
            time_delta_5h = timezone.now() - timezone.timedelta(hours=5)
            time_delta_24h = timezone.now() - timezone.timedelta(hours=24)
            return queryset.filter(
                last_login__lt=time_delta_5h, last_login__gt=time_delta_24h
            )

        if self.value() == "24h-3d":
            time_delta_24h = timezone.now() - timezone.timedelta(hours=24)
            time_delta_3d = timezone.now() - timezone.timedelta(days=3)
            return queryset.filter(
                last_login__lt=time_delta_24h, last_login__gt=time_delta_3d
            )

        if self.value() == "3d-10d":
            time_delta_3d = timezone.now() - timezone.timedelta(days=3)
            time_delta_10d = timezone.now() - timezone.timedelta(days=10)
            return queryset.filter(
                last_login__lt=time_delta_3d, last_login__gt=time_delta_10d
            )

        if self.value() == "10d-1m":
            time_delta_10d = timezone.now() - timezone.timedelta(days=10)
            time_delta_1m = timezone.now() - timezone.timedelta(days=30)
            return queryset.filter(
                last_login__lt=time_delta_10d, last_login__gt=time_delta_1m
            )

        if self.value() == "more than 1m":
            time_delta_1m = timezone.now() - timezone.timedelta(days=30)
            return queryset.filter(last_login__lt=time_delta_1m)

        return queryset


@admin.register(RealUser)
class UserAdmin(PaginatedBaseAdmin):
    change_user_password_template = None
    list_display = [
        "username",
        "fullName",
        "socialProvider",
        "gender",
        "is_staff",
        "is_superuser",
        "last_login",
        "date_joined",
        "coins",
        "user_images",
        "user_deleted_at",
        "is_deleted",
    ]
    search_fields = ["id", "username", "fullName", "email", ]
    list_filter = (
        "gender",
        CoinPurchaseFilter,
        InactiveFromFilter,
        UserOnlineFilter,
        IsDeletedFilter,
        IsDeletedFilterFilter,
        "age",
    )
    exclude = ("password", "user_permissions", )
    filter_horizontal = (
        "blockedUsers",
        "groups",
    )
    fields = [
        'last_login', 'is_superuser', 'groups', 'username',
        'first_name', 'last_name', 'is_staff', 'is_active',
        'date_joined', 'email', 'twitter', 'facebook_id',
        'fullName', 'gender', 'about', 'language',
        'language_id_code', 'location', 'address', 'country',
        'country_code', 'city', 'state', 'isOnline',
        'familyPlans', 'tags', 'politics', 'gift_coins',
        'gift_coins_date', 'purchase_coins', 'purchase_coins_date',
        'active_package', 'zodiacSign', 'interestedIn',
        'interested_in', 'ethinicity', 'religion', 'blockedUsers',
        'is_blocked', 'education', 'music', 'height', 'age',
        'tvShows', 'sportsTeams', 'movies', 'work', 'book', 'likes',
        'photos_quota', 'avatar_index', 'owned_by',
        'broadcast_read_upto', 'broadcast_deleted_upto',
        'firstmessage_read_upto', 'onesignal_player_id', 'roles',
        'user_last_seen', 'notification_sent', 'notified_count',
        'paste_access', 'zip_code', 'note', 'is_deleted', 'id',
        'password', 'user_deleted_at',
    ]
    readonly_fields = (
        "id", "password", "user_deleted_at", "active_package",
    )
    change_password_form = AdminPasswordChangeForm

    order_by = [
        "user_name",
        "coins",
    ]

    actions = ["soft_delete"]

    include_deleted = False

    def _get_user_active_package(self, pkg):
        if not pkg.renewed_package.exists():
            return pkg.package

        return self._get_user_active_package(pkg.renewed_package.last())

    def active_package(self, obj):
        return self._get_user_active_package(obj.packages.last()) if obj.packages.exists() else 'FREE'

    def coins(self, obj):
        return obj.purchase_coins + obj.gift_coins

    def soft_delete(self, request, queryset):
        """Soft delete"""
        # Perform the desired action on the selected objects
        for obj in queryset:
            obj.is_deleted = True
            obj.save()

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('packages').exclude(
            Q(roles__role__in=["CHATTER", "ADMIN", "MODERATOR"]) |
            Q(email__endswith="i69app.com") |
            Q(groups__isnull=False) |
            Q(is_staff=True)
        ).filter(is_deleted=self.include_deleted)
        queryset = queryset.order_by(F("last_login").desc(nulls_last=True))
        return queryset

    def user_images(self, obj):
        pics = UserPhoto.objects.filter(user=obj)
        strcol = []
        strcol.append('<div style="width:230px"><ul class="mwrap">')
        for pic in pics:
            if pic.file:
                pic_url = pic.file.url
                strcol.append(
                    "<li><a class='mtooltip left' href='javascript:;'><img src='"
                    + pic_url
                    + "' width='30px'/><span><img src='"
                    + pic_url
                    + "' style='max-width:300px;max-height:300px;'/></span></a></li>"
                )
            else:
                pic_url = ""
                if not pic.file_url:
                    pic.file_url = ""
                strcol.append(
                    "<li><a class='mtooltip left' href='javascript:;'><img src='"
                    + pic.file_url
                    + "' width='30px'/><span><img src='"
                    + pic_url
                    + "' style='max-width:300px;max-height:300px;'/></span></a></li>"
                )

        strcol.append("</ul></div>")
        style_css = """
        <style>
        a.mtooltip { outline: none; cursor: help; text-decoration: none; position: relative;}
        a.mtooltip span {margin-left: -999em; padding:5px 6px; position: absolute; width:auto; white-space:nowrap; line-height:1.5;box-shadow:0px 0px 10px #999; -moz-box-shadow:0px 0px 10px #999; -webkit-box-shadow:0px 0px 10px #999; border-radius:3px 3px 3px 3px; -moz-border-radius:3px; -webkit-border-radius:3px;}
        a.mtooltip span img {max-width:300px;}
        a.mtooltip {background:#ffffff; text-decoration:none;cursor: help;} /*BG color is a must for IE6*/
        a.mtooltip:hover span{ right: 1em;top: 2em; margin-left: 0; z-index:99999; position:absolute; background:#ffffff; border:1px solid #cccccc; color:#6c6c6c;}

        #changelist-form .results{overflow-x: initial!important;}
        ul.mwrap {list-style:none;}
        ul.mwrap li{margin:0; padding:3px;list-style:none;float:left;}
        ul.mwrap li:nth-child(5n+1) {clear:left;}
        </style>
        """
        strcol.append(style_css)

        return mark_safe("".join(strcol))

    def save_model(self, request, obj, form, change):
        if not form.is_valid():
            return super().save_model(request, obj, form, change)

        if ("purchase_coins" in form.changed_data) or ("gift_coins" in form.changed_data):
            username = form.cleaned_data["username"]
            user = User.objects.filter(username=username).last()
            sender = request.user

            if "purchase_coins" in form.changed_data:
                coins = form.cleaned_data["purchase_coins"]
                changed_coins = int(coins) - int(user.purchase_coins)
                notification_obj = Notification(
                    sender=sender, user=user, notification_setting_id="ADMIN"
                )
                data = {"coins": str(coins)}
                notification_obj.data = data

                try:
                    send_notification_fcm(
                        notification_obj, coins=changed_coins, current_coins=coins
                    )
                except Exception as e:
                    raise Exception(str(e))

            if "gift_coins" in form.changed_data:
                coins = form.cleaned_data["gift_coins"]
                changed_coins = int(coins) - int(user.gift_coins)

                notification_obj = Notification(
                    sender=sender, user=user, notification_setting_id="ADMIN"
                )
                data = {"coins": str(coins)}
                notification_obj.data = data
                try:
                    send_notification_fcm(
                        notification_obj, coins=changed_coins, current_coins=coins
                    )
                except Exception as e:
                    raise Exception(str(e))

        return super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during user creation
        """
        defaults = {}
        defaults.update(kwargs)
        defaults.update(
            {
                "help_texts": {
                    "password": 'To change password use <a href="../password/">this form</a>'
                }
            }
        )
        return super().get_form(request, obj, **defaults)

    def get_urls(self):
        return [
            path(
                "<id>/password/",
                self.admin_site.admin_view(self.user_change_password),
                name="auth_user_password_change",
            ),
        ] + super().get_urls()

    def lookup_allowed(self, lookup, value):
        return not lookup.startswith("password") and super().lookup_allowed(
            lookup, value
        )

    @sensitive_post_parameters_m
    @csrf_protect_m
    def add_view(self, request, form_url="", extra_context=None):
        with transaction.atomic(using=router.db_for_write(self.model)):
            return self._add_view(request, form_url, extra_context)

    def _add_view(self, request, form_url="", extra_context=None):
        # It's an error for a user to have add permission but NOT change
        # permission for users. If we allowed such users to add users, they
        # could create superusers, which would mean they would essentially have
        # the permission to change users. To avoid the problem entirely, we
        # disallow users from adding users if they don't have change
        # permission.
        if not self.has_change_permission(request):
            if self.has_add_permission(request) and settings.DEBUG:
                # Raise Http404 in debug mode so that the user gets a helpful
                # error message.
                raise Http404(
                    'Your user does not have the "Change user" permission. In '
                    "order to add users, Django requires that your user "
                    'account have both the "Add user" and "Change user" '
                    "permissions set."
                )
            raise PermissionDenied

        if extra_context is None:
            extra_context = {}

        username_field = self.model._meta.get_field(self.model.USERNAME_FIELD)
        defaults = {
            "auto_populated_fields": (),
            "username_help_text": username_field.help_text,
        }
        extra_context.update(defaults)
        return super().add_view(request, form_url, extra_context)

    @sensitive_post_parameters_m
    def user_change_password(self, request, id, form_url=""):
        user = self.get_object(request, unquote(id))
        if not self.has_change_permission(request, user):
            raise PermissionDenied

        if not user:
            raise Http404(
                _("%(name)s object with primary key %(key)r does not exist.")
                % {
                    "name": self.model._meta.verbose_name,
                    "key": escape(id),
                }
            )

        if request.method == "POST":
            form = self.change_password_form(user, request.POST)
            if form.is_valid():
                form.save()
                change_message = self.construct_change_message(request, form, None)
                self.log_change(request, user, change_message)
                msg = _("Password changed successfully.")
                messages.success(request, msg)
                update_session_auth_hash(request, form.user)
                return HttpResponseRedirect(
                    reverse(
                        "%s:%s_%s_change"
                        % (
                            self.admin_site.name,
                            user._meta.app_label,
                            self.model._meta.model_name,
                        ),
                        args=(user.pk,),
                    )
                )
        else:
            form = self.change_password_form(user)

        fieldsets = [(None, {"fields": list(form.base_fields)})]
        adminForm = admin.helpers.AdminForm(form, fieldsets, {})

        context = {
            "title": _("Change password: %s") % escape(user.get_username()),
            "adminForm": adminForm,
            "form_url": form_url,
            "form": form,
            "is_popup": (IS_POPUP_VAR in request.POST or IS_POPUP_VAR in request.GET),
            "add": True,
            "change": False,
            "has_delete_permission": False,
            "has_change_permission": True,
            "has_absolute_url": False,
            "opts": self.model._meta,
            "original": user,
            "save_as": False,
            "show_save": True,
            **self.admin_site.each_context(request),
        }

        request.current_app = self.admin_site.name

        return TemplateResponse(
            request,
            self.change_user_password_template
            or "admin/auth/user/change_password.html",
            context,
        )


class DeletedRealUser(User):

    class Meta:
        proxy = True
        verbose_name = '_Deleted Real User'
        verbose_name_plural = '_Deleted Real Users'


@admin.register(DeletedRealUser)
class DeletedRealUsersAdmin(UserAdmin):
    actions = []

    include_deleted = True


class UserStaff(User):
    class Meta:
        proxy = True
        verbose_name = "_User Admin"
        verbose_name_plural = "_User Admins"


@admin.register(UserStaff)
class UserStaffAdmin(UserAdmin):
    def get_queryset(self, request):
        qs = User.objects.filter(roles__role__in=["ADMIN"])
        return qs


class UserModerator(User):
    class Meta:
        proxy = True
        verbose_name = "_User Moderator"
        verbose_name_plural = "_User Moderators"

    @property
    def is_online(self):
        """
        Checks if the Current moderator is online or offline
        :return:
        """
        if self.moderator_schedule:
            now_ = timezone.now().time()
            return self.moderator_schedule.online_time <= now_ and self.moderator_schedule.offline_time >= now_
        return False


@admin.register(UserModerator)
class UserModeratorAdmin(UserAdmin):
    def get_queryset(self, request):
        qs = User.objects.filter(
            Q(roles__role__in=["MODERATOR"]) | Q(email__endswith="i69app.com") & ~Q(roles__role__in=["ADMIN"])
        )
        return qs


class UserWorker(User):
    class Meta:
        proxy = True
        verbose_name = "_Worker"
        verbose_name_plural = "_Workers"


@admin.register(UserWorker)
class UserWorkerAdmin(UserAdmin):
    def get_queryset(self, request):
        qs = User.objects.filter(roles__role__in=["CHATTER"])
        return qs


@admin.register(UserSocialProfile)
class UserSocialProfileAdmin(ImportExportModelAdmin, ExportActionMixin, admin.ModelAdmin):
    pass


class CoinSettingsForRegionInline(admin.TabularInline):
    model = CoinSettingsForRegion
    extra = 0
    can_delete = False


@admin.register(Country)
class CountryAdmin(ImportExportModelAdmin, ExportActionMixin, admin.ModelAdmin):
    search_fields = ["name", "full_name"]
    exclude = ('full_name',)
    form = select2_modelform(Country, attrs={'width': '250px'})


@admin.register(CoinSettingsRegion)
class CoinSettingsRegionAdmin(ImportExportModelAdmin, ExportActionMixin, admin.ModelAdmin):
    search_fields = ["title"]
    filter_horizontal = ["countries"]
    form = CoinSettingsRegionForm


@admin.register(CoinSettings)
class CoinSettingsAdmin(ImportExportModelAdmin, ExportActionMixin, admin.ModelAdmin):
    search_fields = ["method", "coins_needed"]
    inlines = [CoinSettingsForRegionInline]


class AdminImageWidget(ClearableFileInput):
    def render(self, name, value, attrs=None, renderer=None):
        output = []
        if value and getattr(value, "url", None):
            image_url = value.url
            file_name = str(value)
            output.append(
                '<a href="%s" target="_blank">'
                '<img src="%s" alt="%s" style="max-width: 200px; max-height: 200px; border-radius: 5px;" />'
                "</a><br/><br/> " % (image_url, image_url, file_name)
            )
        output.append(super(ClearableFileInput, self).render(name, value, attrs))

        return mark_safe("".join(output))


class UserPhotoAdminForm(forms.ModelForm):
    class Meta:
        model = UserPhoto
        fields = "__all__"
        widgets = {"file": AdminImageWidget}


@admin.register(UserPhoto)
class UserPhotoAdmin(PaginatedBaseAdmin):
    list_display = ("id", "user", "created_at", "view_thumbnail")
    search_fields = ["user__username", "user__fullName", "user__email"]
    form = UserPhotoAdminForm

    def view_thumbnail(self, obj):
        output = []
        if obj.file:
            image_url = obj.file.url
            output.append(
                '<a href="javascript:;" class="mtooltip left">'
                '<img src="%s" alt="" style="max-width: 30px; max-height: 30px;" />'
                '<span><img src="%s" style="max-width: 300px; max-height: 300px;"/></span>'
                "</a>" % (image_url, image_url)
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
        if obj.file_url:
            image_url = obj.file_url
            output.append(
                '<a href="javascript:;" class="mtooltip left">'
                '<img src="%s" alt="" style="max-width: 30px; max-height: 30px;" />'
                '<span><img src="%s" style="max-width: 300px; max-height: 300px;"/></span>'
                "</a>" % (image_url, image_url)
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


@admin.register(PrivateUserPhoto)
class PrivateUserPhotoAdmin(ModelAdmin):
    list_display = ("id", "user", "created_at", "view_thumbnail")
    search_fields = ["user__username", "user__fullName", "user__email"]
    form = UserPhotoAdminForm

    def view_thumbnail(self, obj):
        output = []
        if obj.file:
            image_url = obj.file.url
            output.append(
                '<a href="javascript:;" class="mtooltip left">'
                '<img src="%s" alt="" style="max-width: 30px; max-height: 30px;" />'
                '<span><img src="%s" style="max-width: 300px; max-height: 300px;"/></span>'
                "</a>" % (image_url, image_url)
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
        if obj.file_url:
            image_url = obj.file_url
            output.append(
                '<a href="javascript:;" class="mtooltip left">'
                '<img src="%s" alt="" style="max-width: 30px; max-height: 30px;" />'
                '<span><img src="%s" style="max-width: 300px; max-height: 300px;"/></span>'
                "</a>" % (image_url, image_url)
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


@admin.register(PrivatePhotoViewTime)
class PrivatePhotoViewTimeAdmin(ModelAdmin):
    pass


@admin.register(PrivatePhotoViewRequest)
class PrivatePhotoViewRequestAdmin(ModelAdmin):
    pass


class ReviewUserPhotoAdmin(DjangoObjectActions, PaginatedBaseAdmin):
    list_display = ["user_photo", "id", "created_at", "view_thumbnail"]
    readonly_fields = ["view_thumbnail"]
    change_actions = ("approve_picture", "move_to_private", "reject_picture")
    search_fields = [
        "user_photo__id",
        "user_photo__user__username",
        "user_photo__user__fullName",
        "user_photo__user__email",
    ]

    def view_thumbnail(self, obj):
        output = []
        if obj.file:
            image_url = obj.file.url
            output.append(
                '<a href="javascript:;" class="mtooltip left">'
                '<img src="%s" alt="" style="max-width: 300px; max-height: 300px;" />'
                '<span><img src="%s" style="max-width: 300px; max-height: 300px;"/></span>'
                "</a>" % (image_url, image_url)
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

    def approve_picture(self, request, obj):
        user_photo = obj.user_photo
        user_photo.file = obj.file
        user_photo.is_admin_approved = True
        user_photo.save()  # update real picture

        notification_obj = Notification(
            user=user_photo.user,
            notification_setting_id=PIC_REVIEW_NOTIFICATION_SETTING,
            data={},
        )  # create notification
        send_notification_fcm(
            notification_obj=notification_obj, status="approved"
        )  # send push notification
        obj.delete()  # delete review object
        return HttpResponseRedirect("/admin/user/reviewuserphoto/")

    def move_to_private(self, request, obj):
        user_photo_obj = obj.user_photo
        user = user_photo_obj.user
        PrivateUserPhoto.objects.create(
            file=obj.file,
            user=user,
            is_admin_approved=True
        )
        notification_obj = Notification(
            user=user,
            notification_setting_id=PIC_REVIEW_NOTIFICATION_SETTING,
            data={}
        )
        send_notification_fcm(
            notification_obj=notification_obj, status='moved_to_private'
        )
        obj.delete()
        user_photo_obj.delete()
        return HttpResponseRedirect("/admin/user/reviewuserphoto/")

    def reject_picture(self, request, obj):
        notification_obj = Notification(
            user=obj.user_photo.user,
            notification_setting_id=PIC_REVIEW_NOTIFICATION_SETTING,
            data={},
        )  # create notification
        send_notification_fcm(
            notification_obj=notification_obj, status="rejected"
        )  # send push notification
        obj.delete()  # delete review object
        return HttpResponseRedirect("/admin/user/reviewuserphoto/")


@admin.register(UserLimit)
class UserLimitAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if form.is_valid():
            if ("limit_value" in form.changed_data and request.POST["action_name"] == "FreeProfilePhotos"):
                User.objects.filter(owned_by=None, is_staff=False).exclude(
                    roles__role__in=["CHATTER", "ADMIN", "MODERATOR"]
                ).update(photos_quota=form.cleaned_data["limit_value"])

        super().save_model(request, obj, form, change)


class GiftedCoins(User):
    class Meta:
        proxy = True
        verbose_name = "Gifted Coin"
        verbose_name_plural = "Gifted Coins"


class PurchasedCoins(User):
    class Meta:
        proxy = True
        verbose_name = "Purchased Coin"
        verbose_name_plural = "Purchased Coins"


class PerHourFilter(SimpleListFilter):
    parameter_name = "hour"
    title = "Hour"
    column = "created_at"

    def lookups(self, request, model_admin):
        if f"{self.column}__day" in request.GET or not any(
            key in request.GET
            for key in (f"{self.column}__year", f"{self.column}__month")
        ):
            qs = model_admin.get_queryset(request)
            now = timezone.now()
            day = request.GET.get(f"{self.column}__day", now.day)
            month = request.GET.get(f"{self.column}__month", now.month)
            year = request.GET.get(f"{self.column}__year", now.year)
            values = qs.filter(
                **{
                    f"{self.column}__year": year,
                    f"{self.column}__month": month,
                    f"{self.column}__day": day,
                }
            ).values_list(f"{self.column}", flat=True)
            hours = list(set([str(val.hour) for val in values]))
            hours_val_map = {
                "1": ("1AM", "1 AM"),
                "2": ("2AM", "2 AM"),
                "3": ("3AM", "3 AM"),
                "4": ("4AM", "4 AM"),
                "5": ("5AM", "5 AM"),
                "6": ("6AM", "6 AM"),
                "7": ("7AM", "7 AM"),
                "8": ("8AM", "8 AM"),
                "9": ("9AM", "9 AM"),
                "10": ("10AM", "10 AM"),
                "11": ("11AM", "11 AM"),
                "12": ("12PM", "12 PM"),
                "13": ("1PM", "1 PM"),
                "14": ("2PM", "2 PM"),
                "15": ("3PM", "3 PM"),
                "16": ("4PM", "4 PM"),
                "17": ("5PM", "5 PM"),
                "18": ("6PM", "6 PM"),
                "19": ("7PM", "7 PM"),
                "20": ("8PM", "8 PM"),
                "21": ("9PM", "9 PM"),
                "22": ("10PM", "10 PM"),
                "23": ("11PM", "11 PM"),
                "0": ("12AM", "12 AM"),
            }
            valid_hours = [v for k, v in hours_val_map.items() if k in hours]
            return valid_hours
        else:
            return []

    def queryset(self, request, queryset):
        time_values_map = {
            "1AM": 1,
            "2AM": 2,
            "3AM": 3,
            "4AM": 4,
            "5AM": 5,
            "6AM": 6,
            "7AM": 7,
            "8AM": 8,
            "9AM": 9,
            "10AM": 10,
            "11AM": 11,
            "12PM": 12,
            "1PM": 13,
            "2PM": 14,
            "3PM": 15,
            "4PM": 16,
            "5PM": 17,
            "6PM": 18,
            "7PM": 19,
            "8PM": 20,
            "9PM": 21,
            "10PM": 22,
            "11PM": 23,
            "12AM": 0,
        }
        if f"{self.column}__day" in request.GET or not any(
            key in request.GET
            for key in (f"{self.column}__year", f"{self.column}__month")
        ):
            if time_values_map.get(self.value()) is not None:
                now = timezone.now()
                day = request.GET.get(f"{self.column}__day", now.day)
                month = request.GET.get(f"{self.column}__month", now.month)
                year = request.GET.get(f"{self.column}__year", now.year)
                hour = time_values_map.get(self.value())
                return queryset.filter(
                    **{
                        f"{self.column}__year": year,
                        f"{self.column}__month": month,
                        f"{self.column}__day": day,
                        f"{self.column}__hour": hour,
                    }
                )
        return queryset


class GiftedCoinsHourFilter(PerHourFilter):
    column = "gift_coins_date"


class PurchaseMethodFilter(SimpleListFilter):
    title = "Purchase Method"
    parameter_name = "purchase_method"
    payments = [p[0] for p in payment_method_choices]

    def lookups(self, request, model_admin):
        return payment_method_choices

    def queryset(self, request, queryset):
        value = self.value()
        if value in self.payments:
            purchase_user_ids = (
                Purchase.objects.filter(payment_method=value)
                .values("user_id")
                .annotate(purchase_id=Max("purchase_id"))
            )
            purchase_user_ids = list(
                set([str(uid["user_id"]) for uid in purchase_user_ids])
            )
            return queryset.filter(id__in=purchase_user_ids)

        return queryset


class PurchasedCoinsHourFilter(PerHourFilter):
    column = "purchase_coins_date"


class CoinsDateFilter(SimpleListFilter):
    template = "admin/user/purchasedcoins/filter.html"
    title: str = "Location"
    parameter_name = "locations"


def custom_titled_filter(title):
    class Wrapper(admin.FieldListFilter):
        def __new__(cls, *args, **kwargs):
            instance = admin.FieldListFilter.create(*args, **kwargs)
            instance.title = title
            return instance

    return Wrapper


class GiftedCoinsAdmin(PaginatedBaseAdmin):
    list_display = ["username", "gift_coins", "gift_coins_date", "country"]
    ordering = (F("gift_coins_date").desc(nulls_last=True),)
    order_by = ("username", "gift_coins", "gift_coins_date")
    search_fields = ["username", "fullName", "email"]
    list_filter = (
        ("country", custom_titled_filter("Location")),
        GiftedCoinsHourFilter
    )
    date_hierarchy = "gift_coins_date"

    def get_queryset(self, request):
        return User.objects.filter(Q(gift_coins__gte=1)).order_by("username")

    def get_gift_history_list(self, user_id):
        return Giftpurchase.objects.filter(receiver=user_id).order_by("-purchased_on")

    def change_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        user = User.objects.get(pk=object_id)
        extra_context["gift_history_list"] = self.get_gift_history_list(
            user_id=user.id)
        return super(GiftedCoinsAdmin, self).history_view(
            request,
            object_id,
            extra_context=extra_context,
        )

    def has_add_permission(self, request, obj=None):
        return False


class PurchasedCoinsAdmin(PaginatedBaseAdmin):
    list_display = [
        "username",
        "purchase_coins",
        "purchase_coins_date",
        "country",
        "purchase_method",
        "currency",
    ]
    ordering = (F("purchase_coins_date").desc(nulls_last=True),)
    order_by = ("username", "purchase_coins", "purchase_coins_date")
    search_fields = ["username", "fullName", "email"]
    list_filter = (
        ("country", custom_titled_filter("Location")),
        PurchaseMethodFilter,
        PurchasedCoinsHourFilter,
    )
    date_hierarchy = "purchase_coins_date"

    def get_queryset(self, request):
        return User.objects.filter(Q(purchase_coins__gte=1)).order_by("username")

    def get_purchase_history_list(self, user_id):
        return (
            CoinsHistory.objects.filter(user_id=user_id)
            .filter(purchase_coins__gte=1)
            .order_by("-date_created")
        )

    def currency(self, obj):
        currency = Purchase.objects.filter(
            user=obj
        ).values_list("currency", flat=True)
        if currency:
            return ", ".join(
                list(set([str(pm)
                     for pm in currency if pm is not None and pm != ""]))
            )
        return None

    def purchase_method(self, obj):
        purchase = (
            Purchase.objects.filter(user=obj)
            .order_by("-purchased_on")
            .values_list("payment_method", flat=True)
        )
        if purchase:
            return ", ".join(
                list(set([str(pm)
                     for pm in purchase if pm is not None and pm != ""]))
            )
        return None

    def change_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        user = User.objects.get(pk=object_id)
        extra_context["purchase_history_list"] = self.get_purchase_history_list(
            user_id=user.id
        )
        return super(PurchasedCoinsAdmin, self).history_view(
            request,
            object_id,
            extra_context=extra_context,
        )

    def has_add_permission(self, request, obj=None):
        return False


class ModeratorStatusFilter(SimpleListFilter):
    title = "Moderator Status"
    parameter_name = "mod_status"

    def lookups(self, request, model_admin):
        return [
            ("Online", "Online"),
            ("Offline", "Offline"),
        ]

    def queryset(self, request, queryset):
        now_ = timezone.now().time()
        if self.value() == "Offline":
            queryset = queryset.filter(
                Q(moderator__moderator_schedule__online_time__gt=now_) |
                Q(moderator__moderator_schedule__offline_time__lt=now_)
            )

        if self.value() == "Online":
            queryset = queryset.filter(
                moderator__moderator_schedule__online_time__lte=now_,
                moderator__moderator_schedule__offline_time__gte=now_
            )

        return queryset


class ChatsQueAdmin(PaginatedBaseAdmin):

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter(room_id__in=Room.objects.all().values('id'))
        return qs

    list_filter = [
        ModeratorStatusFilter
    ]

    list_display = [
        "room_id",
        "moderator",
        "worker",
        "isAssigned",
        "updated_at",
        "date_created"
    ]

    search_fields = [
        "room_id",
        "moderator",
        "worker__username",
        "worker__fullName",
        "worker__email",
        "isAssigned",
    ]

    ordering = ["-isAssigned"]


class ModeratorOnlineSchedulerAdmin(PaginatedBaseAdmin):
    search_fields = ["list_name", "moderator_list__username"]

    def get_form(self, request, obj=None, **kwargs):
        defaults = {}
        defaults.update(kwargs)
        form = super().get_form(request, obj, **defaults)

        qs = get_user_model().objects.filter(roles__role__in=["MODERATOR"])
        if obj:
            moderators = ModeratorOnlineScheduler.moderator_list.through.objects.exclude(
                user_id__in=obj.moderator_list.values_list("id", flat=True)
            ).values_list("user_id", flat=True)
            qs = qs.exclude(id__in=moderators)
        else:
            qs = qs.exclude(
                id__in=ModeratorOnlineScheduler.moderator_list.through.objects.values_list(
                    "user_id", flat=True
                ).distinct()
            )

        moderator_list = forms.ModelMultipleChoiceField(
            queryset=qs,
            to_field_name="id",
            required=False,
            widget=FilteredSelectMultipleM2M("Name", is_stacked=False),
        )
        form.base_fields["moderator_list"] = moderator_list
        return form


class SettingsAdmin(admin.ModelAdmin):
    list_display = ["key", "value", "description"]


class UserNewAdmin(admin.ModelAdmin):
    search_fields = [
        "email",
        "fullName",
        "username",
    ]
    list_display = [
        "username", "email",
        "is_active", "date_joined",
        'user_language_code',
    ]
    ordering = ["-date_joined"]


class StaticDeviceNewAdmin(ModelAdmin):
    change_user_password_template = None
    list_display = ["user", ]

    search_fields = ["user__email", "user__username", ]
    inlines = [
        StaticTokenInline,
    ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(roles__role__in=["ADMIN"])

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class DeleteAccountSettingAdmin(ModelAdmin):
    list_display = ['is_delete_account_allowed']

    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False

        return super().has_add_permission(request)


@admin.register(FailedFCMMessage)
class FailedFcmMessageAdmin(admin.ModelAdmin):
    list_display = ["gcm_device", "user", "error_message", "created_at"]

    def user(self, obj):
        return f"{obj.gcm_device.user.username}"


@admin.register(ProfileFollow)
class ProfileFollowAdmin(admin.ModelAdmin):
    list_display = ["follower", "following", "created_at"]
    list_select_related = ('follower', 'following',)
    search_fields = (
        'follower__id',
        'follower__fullName',
        'follower__username',
        'follower__first_name',
        'follower__last_name',
        'follower__email',
        'following__id',
        'following__fullName',
        'following__username',
        'following__first_name',
        'following__last_name',
        'following__email',
    )


@admin.register(FeatureSettings)
class FeatureSettingsAdmin(admin.ModelAdmin):
    list_display = ["description", "feature_type", "feature_status"]


@admin.register(CoinSpendingHistory)
class CoinSpendingHistoryAdmin(admin.ModelAdmin):
    list_display = ["user", "coins_spent", "description", "created_at"]
    list_select_related = ('user', )
    search_fields = (
        'user__fullName',
        'user__first_name',
        'user__last_name',
        'user__username',
        'user__email',
        'user__id',
    )


@admin.register(UserProfileTranlations)
class UserProfileTranlationsAdmin(admin.ModelAdmin):
    list_display = ["name", "name_fr", "name_zh_cn", "name_nl"]
    search_fields = ["name"]

    class Media:
        js = ("admin/js/admin_paginator.js",)


class UserInterestForRegionInline(admin.TabularInline):
    model = UserInterestForRegion
    extra = 0
    can_delete = True


@admin.register(SetInterestedInRegion)
class UserInterestRegionAdmin(ImportExportModelAdmin, ExportActionMixin, admin.ModelAdmin):
    search_fields = ["title"]
    filter_horizontal = ["countries"]
    form = UserInterestedInRegionForm


@admin.register(UserInterestedIn)
class SetInterestedInAdmin(admin.ModelAdmin):
    list_display = ["str_name",]
    list_filter = ("str_name",)
    inlines = [UserInterestForRegionInline]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ErrorMessageTranslation)
class ErrorMessageTranslationAdmin(admin.ModelAdmin):
    list_display = ["message", "message_fr", "updated_at"]


class UserForModsRestrictionForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=User.objects.filter(
        ~Q(roles__role__in=["CHATTER", "ADMIN", "MODERATOR"]),
        ~Q(is_staff=True),
        ~Q(email__endswith="i69app.com")
    ), widget=Select2(attrs={'width': '250px'}))

    class Meta:
        model = UserForModsRestriction
        fields = ('user', 'moderators')


@admin.register(UserForModsRestriction)
class UserForModsRestrictionAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at"]
    search_fields = ["user__id", "user__username", "user__email"]
    filter_horizontal = ["moderators"]
    form = UserForModsRestrictionForm

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "moderators":
            kwargs["queryset"] = User.objects.filter(
                Q(roles__role__in=["MODERATOR"]) | Q(email__endswith="i69app.com")
            )
            kwargs["to_field_name"] = "id"
            kwargs["required"] = False
            kwargs["widget"] = FilteredSelectMultipleM2M("MODERATOR", is_stacked=False)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def _revert_restriction(self, instance: UserForModsRestriction):
        # Find the rooms with restricted messages for the moderator
        restricted_rooms = (
            Message.objects.values(
                "room_id_id"
            ).annotate(
                count=Count("room_id_id")
            ).filter(
                user_id=instance.user.id,
                restricted_msg=True,
                sender_worker_id=None,
            ).order_by("room_id_id").distinct()
        )
        for restricted_room in restricted_rooms:
            restricted_room_id = restricted_room.get("room_id_id")
            first_restricted_message = Message.objects.filter(
                room_id_id=restricted_room_id, restricted_msg=True,
                sender_worker_id=None
            ).order_by("timestamp").first()
            moderator = (
                first_restricted_message.room_id.target
                if first_restricted_message.room_id.user_id.id == instance.user.id
                else first_restricted_message.room_id.user_id
            )
            # Create a chat Queue
            new_queue = ChatsQue(
                room_id=restricted_room_id,
                moderator=moderator,
                updated_at=timezone.now(),
                isAssigned=False,
            )
            new_queue.save()
            new_queue.date_created = first_restricted_message.timestamp
            new_queue.save()
            # Clear the restricted flag
            Message.objects.filter(
                room_id_id=restricted_room_id, restricted_msg=True,
                timestamp__gte=first_restricted_message.timestamp,
                sender_worker_id=None
            ).update(
                restricted_msg=False
            )

    def delete_queryset(self, request, queryset):
        """Delete Multiple records from Admin List View."""
        for instance in queryset:
            self._revert_restriction(instance=instance)
            # Delete user individually to allow to delete the
            instance.delete()

    def delete_model(self, request, obj):
        """Delete single record from Admin."""
        for instance in [obj]:
            self._revert_restriction(instance=instance)
        return super().delete_model(request=request, obj=obj)

    def save_related(self, request, form, formsets, change):
        old_moderators = [mod.id for mod in form.instance.moderators.all()]
        super().save_related(request=request, form=form, formsets=formsets, change=change)
        instance = form.instance
        moderators = [mod.id for mod in instance.moderators.all()]
        new_moderators = list(set(moderators)-set(old_moderators))
        if new_moderators:
            # Find the rooms with restricted messages for the moderator
            restricted_rooms = (
                Message.objects.values("room_id_id")
                .annotate(count=Count("room_id_id"))
                .filter(
                    user_id=instance.user.id, restricted_msg=True,
                    sender_worker_id=None
                ).filter(
                    Q(room_id__user_id__in=new_moderators) | Q(room_id__target_id__in=new_moderators)
                )
                .order_by("room_id_id")
                .distinct()
            )
            for restricted_room in restricted_rooms:
                restricted_room_id = restricted_room.get("room_id_id")
                first_restricted_message = Message.objects.filter(
                    room_id_id=restricted_room_id, restricted_msg=True,
                    sender_worker_id=None
                ).order_by("timestamp").first()
                moderator = (
                    first_restricted_message.room_id.target
                    if first_restricted_message.room_id.user_id.id == instance.user.id
                    else first_restricted_message.room_id.user_id
                )
                # Create a chat Queue
                new_queue = ChatsQue(
                    room_id=restricted_room_id,
                    moderator=moderator,
                    updated_at=timezone.now(),
                    isAssigned=False,
                )
                new_queue.save()
                new_queue.date_created = first_restricted_message.timestamp
                new_queue.save()
                # Clear the restricted flag
                Message.objects.filter(
                    room_id_id=restricted_room_id, restricted_msg=True,
                    timestamp__gte=first_restricted_message.timestamp,
                    sender_worker_id=None
                ).update(
                    restricted_msg=False
                )

        # Find the CHats in Queue
        chats_in_queue = ChatsQue.objects.filter(
            room_id__in=Room.objects.filter(
                Q(user_id=instance.user.id) | Q(target_id=instance.user.id)
            )
        )
        for chat in chats_in_queue:
            room = Room.objects.get(pk=chat.room_id)
            if not moderators or not (room.user_id in moderators or room.target_id not in moderators):
                Message.objects.filter(
                    room_id=chat.room_id, restricted_msg=False, timestamp__gte=chat.date_created,
                    sender_worker_id=None
                ).update(restricted_msg=True)

                chat.delete()


class ProfileVisitAdmin(admin.ModelAdmin):
    list_display = ('visitor', 'visiting', 'last_visited',)
    list_select_related = ['visitor', 'visiting',]
    search_fields = (
        'visitor__id',
        'visitor__username',
        'visitor__email',
        'visitor__fullName',
        'visiting__id',
        'visiting__username',
        'visiting__email',
        'visiting__fullName',
    )

class CustomGroupAdmin(admin.ModelAdmin):
    list_display = ('name',)
    filter_horizontal = ["permissions"]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "permissions":
            kwargs["queryset"] = Permission.objects.all()
            kwargs["to_field_name"] = "id"
            kwargs["required"] = False
            kwargs["widget"] = FilteredSelectMultipleM2M("PERMISSIONS", is_stacked=False)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


admin.site.register(ChatsQue, ChatsQueAdmin)
admin.site.register(ChatsQueSetting)
admin.site.register(ModeratorOnlineScheduler, ModeratorOnlineSchedulerAdmin)
admin.site.register(UserRole)
admin.site.register(WorkerInvitation)
admin.register(PrivatePhotoViewTime)
admin.register(PrivatePhotoViewRequest)
admin.site.register(BlockedImageAlternatives)
admin.site.register(ReviewUserPhoto, ReviewUserPhotoAdmin)
admin.site.register(GiftedCoins, GiftedCoinsAdmin)
admin.site.register(PurchasedCoins, PurchasedCoinsAdmin)
admin.site.register(Settings, SettingsAdmin)
admin.site.register(User, UserNewAdmin)
admin.site.register(StaticDevice, StaticDeviceNewAdmin)
admin.site.register(DeleteAccountSetting, DeleteAccountSettingAdmin)
admin.site.register(InstagramScrapy, InstagramAdmin)
admin.site.register(ProfileVisit, ProfileVisitAdmin)
admin.site.unregister(Group)
admin.site.register(Group, CustomGroupAdmin)