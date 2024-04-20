from datetime import datetime, timedelta
from itertools import chain

import channels
import channels_graphql_ws
import geopy.distance
import graphene
from django.contrib.auth import get_user_model
from django.db.models import Count, F, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from googletrans import Translator
from graphene.utils.resolve_only_args import resolve_only_args
from graphene_django import DjangoObjectType
from graphql.error import GraphQLError
from push_notifications.models import GCMDevice

import chat.schema
import defaultPicker.schema
import gifts.schema
import moments.schema
import payments
import payments.schema
import purchase.schema
import reports.schema
import stock_image.schema
import user.schema
from defaultPicker.models import Language
from defaultPicker.models import age as Age
from defaultPicker.models import book as Book
from defaultPicker.models import height as Height
from defaultPicker.models import movies as Movies
from defaultPicker.models import music as Music
from defaultPicker.models import sportsTeams as SportsTeams
from defaultPicker.models import tags
from defaultPicker.models import tvShows as TVShow
from defaultPicker.utils import translated_field_name
from framework.constants import USER_ADVANCE_SORTING_FEATURE
from gifts.models import Giftpurchase
from moments.models import Story, StoryReport, User
from moments.schema import ReportType
from moments.utils import modify_text
from purchase.models import Package, PackagePurchase, Permission
from subscriptions.models import ModeratorSubscriptionPlan
from user.models import (CoinSettings, CoinSettingsForRegion,
                         CoinSpendingHistory, PrivatePhotoViewRequest,
                         PrivatePhotoViewTime, ProfileFollow, ProfileVisit,
                         Settings, User, UserProfileTranlations, UserRole,
                         UserSocialProfile)
from user.schema import OnUserOnline, UserPhotoType
from user.tasks import send_notification_to_nearby_users
from user.utils import (get_country_from_geo_point, is_feature_enabled,
                        translate_error_message)

translator = Translator()
userroles = UserRole.objects.filter(role=UserRole.ROLE_FAKE_USER).exists()
if userroles:
    MODERATOR_ID = UserRole.objects.get(role=UserRole.ROLE_FAKE_USER).id
else:
    MODERATOR_ID = 1


class TagResponse(graphene.ObjectType):
    id = graphene.Int()
    tag = graphene.String()
    tag_fr = graphene.String()


class AvatarPhotoMixin:
    avatar_photos = graphene.List(UserPhotoType)

    def resolve_avatar_photos(self, info):
        return self.avatar_photos.all().exclude(file='')


class likedUsersResponse(graphene.ObjectType, AvatarPhotoMixin):
    id = graphene.String()
    username = graphene.String()
    full_name = graphene.String()

    def resolve_full_name(self, info):
        return self.fullName

    def resolve_id(self, info):
        return self.id

    def resolve_username(self, info):
        return self.username


class blockedUsersResponse(graphene.ObjectType, AvatarPhotoMixin):
    id = graphene.String()
    username = graphene.String()
    full_name = graphene.String()

    def resolve_full_name(self, info):
        return self.fullName

    def resolve_id(self, info):
        return self.id

    def resolve_username(self, info):
        return self.username


class InResponse(graphene.ObjectType):
    id = graphene.Int()
    interest = graphene.String()
    interest_fr = graphene.String()


class attrTranslationType(graphene.ObjectType):
    name = graphene.String()
    name_translated = graphene.String()


class UserAttrTranslationType(DjangoObjectType):
    name = graphene.String()

    class Meta:
        model = UserProfileTranlations
        fields = "__all__"

    def resolve_name(self, info):
        return getattr(self, translated_field_name(info.context.user, "name"))


class UserFollowType(DjangoObjectType, AvatarPhotoMixin):
    is_connected = graphene.Boolean()
    datetime = graphene.DateTime()
    datetime_visiting = graphene.DateTime()
    followers_count = graphene.Int()
    following_count = graphene.Int()

    class Meta:
        model = User
        fields = "__all__"

    def resolve_is_connected(self, info):
        requested_user = info.context.user
        user = get_user_model().objects.get(id=self.id)
        if requested_user == user:
            return None
        return ProfileFollow.objects.filter(follower=requested_user, following_id=self.id).exists()

    def resolve_datetime(self, info):
        try:
            latest_visitor = ProfileVisit.objects.filter(
                visitor_id=self.id).order_by("-created_at").first()
            return latest_visitor.created_at
        except:
            return None

    def resolve_datetime_visiting(self, info):
        try:
            latest_visited = ProfileVisit.objects.filter(
                visiting_id=self.id).order_by("-created_at").first()
            return latest_visited.created_at
        except:
            return None

    def resolve_followers_count(self, info):
        return ProfileFollow.objects.filter(following_id=self.id).count()

    def resolve_following_count(self, info):
        return ProfileFollow.objects.filter(follower_id=self.id).count()


class StoryReportType1(DjangoObjectType):
    class Meta:
        model = StoryReport


class StoryType1(DjangoObjectType):
    class Meta:
        model = Story

    story_reports = graphene.List(StoryReportType1)

    def resolve_story_reports(self, info):
        return self.story_for_report.all()

class UserType(DjangoObjectType, AvatarPhotoMixin):
    class Meta:
        model = User
        fields = ("avatar_index",)

    id = graphene.String()
    username = graphene.String()
    first_name = graphene.String()
    last_name = graphene.String()
    fullName = graphene.String()
    email = graphene.String()
    gender = graphene.Int()
    about = graphene.String()
    location = graphene.List(graphene.Float)
    isOnline = graphene.Boolean()
    familyPlans = graphene.Int()
    age = graphene.Int()
    language = graphene.List(graphene.Int)
    language_id_code = graphene.String()
    user_language_code = graphene.String()
    address = graphene.String()
    tags = graphene.List(graphene.Int)
    politics = graphene.Int()
    purchase_coins = graphene.Int()
    gift_coins = graphene.Int()
    coins = graphene.Int()
    zodiacSign = graphene.Int()
    height = graphene.Int()
    photos_quota = graphene.Int()
    interested_in = graphene.List(graphene.Int)
    ethinicity = graphene.Int()
    religion = graphene.Int()
    blocked_users = graphene.List(blockedUsersResponse)
    education = graphene.String()
    music = graphene.List(graphene.String)
    tvShows = graphene.List(graphene.String)
    sportsTeams = graphene.List(graphene.String)
    movies = graphene.List(graphene.String)
    work = graphene.String()
    books = graphene.List(graphene.String)
    avatar = graphene.Field(UserPhotoType)
    avatar_photos = graphene.List(UserPhotoType)
    likes = graphene.List(likedUsersResponse)
    last_seen = graphene.String()
    online = graphene.Boolean()
    received_gifts = graphene.List(gifts.schema.GiftpurchaseType)
    distance = graphene.String()
    private_photo_request_status = graphene.String()
    city = graphene.String()
    state = graphene.String()
    country = graphene.String()
    country_code = graphene.String()
    country_flag = graphene.String()
    followers_count = graphene.Int()
    following_count = graphene.Int()
    is_connected = graphene.Boolean()
    follower_users = graphene.List(UserFollowType)
    following_users = graphene.List(UserFollowType)
    user_visitors_count = graphene.Int()
    user_visiting_count = graphene.Int()
    user_visitors = graphene.List(UserFollowType)
    user_visiting = graphene.List(UserFollowType)
    user_subscription = graphene.Field(purchase.schema.UserSubscriptionType)
    user_attr_translation = graphene.List(UserAttrTranslationType)
    planname = graphene.String()
    is_moderator = graphene.Boolean()
    stories = graphene.List(StoryType1)
    momemts = graphene.List(ReportType)
    zip_code = graphene.String()
    # allow_manual_chat = graphene.Boolean()
    paste_access = graphene.Boolean()
    subscription = graphene.String()
    can_schedule_moment = graphene.Boolean()
    can_schedule_story = graphene.Boolean()

    has_story_quota = graphene.Boolean()
    has_moment_quota = graphene.Boolean()
    can_schedule_moment = graphene.Boolean()
    can_schedule_story = graphene.Boolean()
    can_post_moment = graphene.Boolean()
    can_post_story = graphene.Boolean()

    def resolve_is_moderator(self, info):
        return self.is_fake

    def resolve_stories(self, info):
        return self.story_set.all()

    def resolve_momemts(self, info):
        return self.User_for_report.all()

    def resolve_zip_code(self, info):
        return self.zip_code

    def resolve_paste_access(self, info):
        return self.paste_access

    def resolve_planname(self, info):
        try:
            package_id = PackagePurchase.objects.filter(user__id=self.id)[0].package_id
            planname_user = Package.objects.filter(id=package_id)[0].name
            return planname_user
        except:
            return "Not Active Plan"

    def resolve_distance(self, info):
        return self.distance

    def resolve_avatar(self, info):
        return self.avatar()

    def resolve_received_gifts(self, info):
        return Giftpurchase.objects.filter(receiver_id=self.id)

    def resolve_username(self, info):
        return self.username

    def resolve_first_name(self, info):
        return self.first_name

    def resolve_last_name(self, info):
        return self.last_name

    def resolve_language_id_code(self, info):
        return self.get_language_id_code()

    def resolve_user_language_code(self, info):
        return self.user_language_code

    def resolve_address(self, info):
        return self.address

    def resolve_last_seen(self, info):
        return self.last_seen()

    def resolve_online(self, info):
        return self.isOnline

    def resolve_avatar_photos(self, info):
        avatar_photos = self.avatar_photos.all().exclude(file='')
        return list(chain(avatar_photos, self.private_avatar_photos.all()))

    def resolve_private_photo_request_status(self, info):
        if info.context.user == self:
            return ""

        hours = PrivatePhotoViewTime.objects.last().no_of_hours
        request = PrivatePhotoViewRequest.objects.filter(
            user_to_view=self,
            requested_user=info.context.user,
            updated_at__gte=datetime.now() - timedelta(hours=hours),
        ).first()

        if not request:
            return ""

        if request.status == "P":
            return "Cancel Request"

        return "Request Access"

    def resolve_coins(self, info):
        return self.purchase_coins + self.gift_coins

    def resolve_country_flag(self, info):
        if not self.country_code:
            return ""
        return info.context.build_absolute_uri(f"/static/img/country-flags/png250/{self.country_code}.png")

    @resolve_only_args
    def resolve_likes(self):
        user = get_user_model().objects.get(id=self.id)
        return user.likes.all()

    @resolve_only_args
    def resolve_age(self):
        user = get_user_model().objects.get(id=self.id)
        if user.age:
            return user.age.id
        return None

    @resolve_only_args
    def resolve_language(self):
        user = get_user_model().objects.get(id=self.id)
        if user.language.all().count() > 0:
            return list(user.language.all().values_list('id', flat=True))
        return None

    @resolve_only_args
    def resolve_height(self):
        user = get_user_model().objects.get(id=self.id)
        if user.height:
            return user.height.id
        return Height.objects.last().id

    @resolve_only_args
    def resolve_likes(self):
        user = get_user_model().objects.get(id=self.id)
        return user.likes.all()

    @resolve_only_args
    def resolve_tvShows(self):
        user = get_user_model().objects.get(id=self.id)
        return list(user.tvShows.values_list("interest", flat=True))

    @resolve_only_args
    def resolve_location(self):
        user = get_user_model().objects.get(id=self.id)
        if user.location:
            return list(map(float, user.location.split(",")))
        return []

    @resolve_only_args
    def resolve_books(self):
        user = get_user_model().objects.get(id=self.id)
        return list(user.book.values_list("interest", flat=True))

    @resolve_only_args
    def resolve_sportsTeams(self):
        user = get_user_model().objects.get(id=self.id)
        return list(user.sportsTeams.values_list("interest", flat=True))

    @resolve_only_args
    def resolve_movies(self):
        user = get_user_model().objects.get(id=self.id)
        return list(user.movies.values_list("interest", flat=True))

    @resolve_only_args
    def resolve_music(self):
        user = get_user_model().objects.get(id=self.id)
        return list(user.music.values_list("interest", flat=True))

    @resolve_only_args
    def resolve_tags(self):
        user = get_user_model().objects.get(id=self.id)
        return list(user.tags.values_list("id", flat=True))

    @resolve_only_args
    def resolve_interested_in(self):
        user = get_user_model().objects.get(id=self.id)
        return user.interestedIn_display

    @resolve_only_args
    def resolve_blocked_users(self):
        user = get_user_model().objects.get(id=self.id)
        return user.blockedUsers.all()

    def resolve_is_connected(self, info):
        requested_user = info.context.user
        user = get_user_model().objects.get(id=self.id)
        if requested_user == user:
            return None
        return ProfileFollow.objects.filter(follower=requested_user, following_id=self.id).exists()

    @resolve_only_args
    def resolve_followers_count(self):
        return ProfileFollow.objects.filter(following_id=self.id).count()

    @resolve_only_args
    def resolve_following_count(self):
        return ProfileFollow.objects.filter(follower_id=self.id).count()

    @resolve_only_args
    def resolve_user_visitors_count(self):
        return ProfileVisit.objects.filter(visiting_id=self.id).count()

    @resolve_only_args
    def resolve_user_visiting_count(self):
        return ProfileVisit.objects.filter(visitor_id=self.id).count()

    @resolve_only_args
    def resolve_follower_users(self):
        return User.objects.select_related().filter(user_follower__following__id=self.id)

    @resolve_only_args
    def resolve_following_users(self):
        return User.objects.select_related().filter(user_following__follower__id=self.id)

    @resolve_only_args
    def resolve_user_visitors(self):
        return User.objects.select_related().filter(
            Q(user_visitor__visiting__id=self.id) &
            (Q(roles__role__in=['REGULAR', 'MODERATOR']))
        )

    @resolve_only_args
    def resolve_user_visiting(self):
        return User.objects.select_related().filter(user_visiting__visitor__id=self.id)

    @resolve_only_args
    def resolve_subscription(self):
        subscriptions = ModeratorSubscriptionPlan.objects.filter(moderator_id=self.id).last()
        if subscriptions:
            return subscriptions.subscription.name
        return None

    def resolve_user_subscription(self, info, **kwargs):
        user = info.context.user
        now = timezone.now()
        subscription = PackagePurchase.objects.filter(
            user=user,
            is_active=True,
            starts_at__lte=now,
            ends_at__gte=now,
            renewed_at__isnull=True,
        ).first()

        is_active = True if subscription else False

        return purchase.schema.UserSubscriptionType(
            is_active=is_active,
            package=subscription.package if subscription else None,
            plan=subscription.plan if subscription else None,
            starts_at=subscription.starts_at if subscription else None,
            ends_at=subscription.ends_at if subscription else None,
            cancelled_at=subscription.cancelled_at if subscription else None,
            is_cancelled=False
            if subscription and subscription.cancelled_at is None
            else True,
        )

    def resolve_user_attr_translation(self, info):
        return UserProfileTranlations.objects.order_by('created_at')


class userResponseObj(graphene.ObjectType):
    id = graphene.String()
    username = graphene.String()
    interested_in = graphene.List(graphene.Int)

    @graphene.resolve_only_args
    def resolve_interested_in(self):
        return get_user_model().objects.get(id=self.id).interestedIn_display


class CreateUser(graphene.Mutation):
    user = graphene.Field(UserType)

    class Arguments:
        username = graphene.String(required=True)
        password = graphene.String(required=True)
        email = graphene.String(required=True)
        onesignal_player_id = graphene.String()
        fcm_registration_id = graphene.String()
        language = graphene.List(graphene.Int)

    def mutate(
        self,
        info,
        username,
        password,
        email,
        onesignal_player_id=None,
        fcm_registration_id=None,
        language=None
    ):
        user = get_user_model()(
            username=username, email=email, onesignal_player_id=onesignal_player_id
        )
        user.set_password(password)
        user.save()
        if language:
            for language_id in language:
                languageObj = Language.objects.filter(id=language_id).first()
                if languageObj:
                    user.language.add(languageObj.id)

        if fcm_registration_id:
            GCMDevice.objects.get_or_create(
                registration_id=fcm_registration_id, cloud_message_type="FCM", user=user
            )
        return CreateUser(user=user)


class UpdateProfile(graphene.Mutation):
    class Arguments:
        city = graphene.String()
        country = graphene.String()
        country_code = graphene.String()
        id = graphene.String()
        username = graphene.String()
        fullName = graphene.String()
        email = graphene.String()
        gender = graphene.Int()
        language = graphene.List(graphene.Int)
        user_language_code = graphene.String()
        about = graphene.String()
        location = graphene.List(graphene.Float)
        isOnline = graphene.Boolean()
        familyPlans = graphene.Int()
        age = graphene.Int()
        tag_ids = graphene.List(graphene.Int)
        politics = graphene.Int()
        zodiacSign = graphene.Int()
        height = graphene.Int()
        interested_in = graphene.List(graphene.Int)
        ethinicity = graphene.Int()
        religion = graphene.Int()
        education = graphene.String()
        music = graphene.List(graphene.String)
        tvShows = graphene.List(graphene.String)
        sportsTeams = graphene.List(graphene.String)
        movies = graphene.List(graphene.String)
        work = graphene.String()
        address = graphene.String()
        book = graphene.List(graphene.String)
        avatar_index = graphene.Int()
        onesignal_player_id = graphene.String()
        fcm_registration_id = graphene.String()
        likes = graphene.List(graphene.String)

        url = graphene.String()
        subscription_id = graphene.String()
        platform = graphene.Int(
            description="Number of social platform 1.GOOGLE 2.FACEBOOK 3.INSTAGRAM 4.SNAPCHAT 5.LINKEDIN"
        )
        paste_access = graphene.Boolean()
        zip_code = graphene.String()
        first_name = graphene.String()
        last_name = graphene.String()

    Output = userResponseObj

    def mutate(
        self,
        info,
        id,
        username=None,
        fullName=None,
        language=None,
        user_language_code=None,
        gender=None,
        email=None,
        height=None,
        familyPlans=None,
        about=None,
        location=None,
        age=None,
        avatar_index=None,
        isOnline=None,
        tag_ids=None,
        url=None,
        platform=None,
        politics=None,
        zodiacSign=None,
        interested_in=None,
        ethinicity=None,
        religion=None,
        education=None,
        photos=None,
        onesignal_player_id=None,
        fcm_registration_id=None,
        music=None,
        likes=None,
        book=None,
        movies=None,
        sportsTeams=None,
        tvShows=None,
        work=None,
        address=None,
        subscription_id=None,
        paste_access=None,
        # allow_manual_chat=None,
        zip_code=None,
        first_name=None,
        last_name=None,
        country_code=None,
        city=None,
        country=None,
    ):
        global socialObj
        user = get_user_model().objects.get(id=id)
        try:
            profile = UserSocialProfile.objects.get(user=user)
        except:
            profile = None

        if username:
            user.username = username
        if first_name:
            user.first_name = first_name
        if country_code:
            user.country_code = country_code
        if city:
            user.city = city
        if country:
            user.country = country
        if last_name:
            user.last_name = last_name
        if fullName:
            user.fullName = modify_text(fullName)
        if user_language_code:
            user.user_language_code = user_language_code
        if gender:
            user.gender = gender
        if language:
            user.language.clear()
            for language_id in language:
                languageObj = Language.objects.filter(id=language_id).first()
                if languageObj:
                    user.language.add(languageObj.id)

        if subscription_id:
            sub_obj = ModeratorSubscriptionPlan.objects.filter(moderator=user).first()
            if not sub_obj:
                ModeratorSubscriptionPlan.objects.create(moderator=user, subscription_id=subscription_id)
            else:
                sub_obj.subscription_id = subscription_id
                sub_obj.save()

        if email and email != "":
            user.email = email
        if height:
            user.height_id = height
            heightObj = Height.objects.filter(height=height).first()
            if heightObj:
                user.height = heightObj.height
        if work:
            user.work = work
        if address:
            user.address = address
        if zip_code:
            user.zip_code = zip_code
        if familyPlans:
            user.familyPlans = familyPlans
        if about:
            user.about = modify_text(about)
        if location:
            loc = list(map(str, location))
            user.location = f"{loc[0]}, {loc[1]}"
            country, country_code, state, city, zip_code = get_country_from_geo_point(
                geo_point=location
            )
            user.country = country
            user.country_code = country_code
            user.state = state
            user.city = city

        if age:
            ageObj = Age.objects.filter(id=age).first()
            if ageObj:
                user.age = ageObj
        if isOnline:
            user.isOnline = isOnline
            if user.isOnline:
                OnUserOnline.notify_related_users(user)

        if tag_ids:
            user.tags.clear()
            for tag_id in tag_ids:
                tag = tags.objects.get(id=tag_id)
                if tag:
                    user.tags.add(tag)
        if politics:
            user.politics = politics
        if music:
            user.music.clear()
            for music_ in music:
                m, _ = Music.objects.get_or_create(
                    interest=music_, defaults={"interest": music_}
                )
                user.music.add(m)
        if movies:
            user.movies.clear()
            for movie_ in movies:
                m, _ = Movies.objects.get_or_create(
                    interest=movie_, defaults={"interest": movie_}
                )
                user.movies.add(m)
        if sportsTeams:
            user.sportsTeams.clear()
            for team in sportsTeams:
                t, _ = SportsTeams.objects.get_or_create(
                    interest=team, defaults={"interest": team}
                )
                user.sportsTeams.add(t)
        if likes:
            user.likes.clear()
            for user_id in likes:
                user_ = get_user_model().objects.get(id=user_id)
                if user_:
                    user.likes.add(user_)
        if book:
            user.book.clear()
            for book_title in book:
                b, _ = Book.objects.get_or_create(
                    interest=book_title, defaults={"interest": book_title}
                )
                user.book.add(b)
        if tvShows:
            user.tvShows.clear()
            for show in tvShows:
                s, _ = TVShow.objects.get_or_create(
                    interest=show, defaults={"interest": show}
                )
                user.tvShows.add(s)
        if zodiacSign:
            user.zodiacSign = zodiacSign
        if interested_in:
            user.interested_in = ",".join(str(i) for i in interested_in)
        if ethinicity:
            user.ethinicity = ethinicity
        if religion:
            user.religion = religion
        if education:
            user.education = education
        if avatar_index:
            user.avatar_index = avatar_index
        if onesignal_player_id:
            user.onesignal_player_id = onesignal_player_id
        if fcm_registration_id:
            GCMDevice.objects.get_or_create(
                registration_id=fcm_registration_id, cloud_message_type="FCM", user=user
            )
        if paste_access:
            user.paste_access = paste_access

        if platform and url and not profile:
            new_profile = UserSocialProfile.objects.create(
                url=url, platform=platform, user=user
            )
            new_profile.save()
        elif profile and url:
            profile.url = url
            profile.save()
        elif profile and platform:
            profile.platform = platform
            profile.save()

        user.save()
        send_notification_to_nearby_users.apply_async(args=[str(id)])
        return userResponseObj(id=user.id, username=user.username)


class DeleteProfileResponse(graphene.ObjectType):
    result = graphene.String()


class DeleteProfile(graphene.Mutation):
    class Arguments:
        id = graphene.String()

    Output = DeleteProfileResponse

    def mutate(self, info, id):
        try:
            u = User.objects.get(id=id)
            if info.context.user.id != u.id:
                raise GraphQLError(
                    message="You are not authorized to delete this account"
                )

            u.is_deleted = True
            u.save()
            return DeleteProfileResponse(result="Profile deleted.")
        except User.DoesNotExist:
            raise Exception(translate_error_message(
                info.context.user, "Account does not exist"))


class Mutation(
    user.schema.Mutation,
    reports.schema.Mutation,
    purchase.schema.Mutation,
    payments.schema.Mutation,
    chat.schema.Mutation,
    moments.schema.Mutation,
    gifts.schema.Mutation,
    stock_image.schema.Mutation,
    graphene.ObjectType,
):
    create_user = CreateUser.Field()
    updateProfile = UpdateProfile.Field()
    deleteProfile = DeleteProfile.Field()


class permissionType(graphene.ObjectType):
    has_permission = graphene.Boolean()
    coins_to_unlock = graphene.Int()
    free_user_limit = graphene.Int()


class UserSearchAndPermissionType(graphene.ObjectType):
    user = graphene.List(UserType)
    my_permission = graphene.Field(permissionType)


def get_user_search_permission(permission, user):
    now = timezone.now()
    has_permision = False

    subscription = PackagePurchase.objects.filter(
        user=user, is_active=True, starts_at__lte=now, ends_at__gte=now
    ).first()

    if subscription:
        permissions = [
            *Permission.objects.filter(package=subscription.package).values_list(
                "name", flat=True
            )
        ]
        if permission in permissions:
            has_permision = True
    return has_permision


class Translation(graphene.ObjectType):
    text = graphene.String()
    translated_text = graphene.String()
    language = graphene.String()


class Query(
    chat.schema.Query,
    defaultPicker.schema.Query,
    user.schema.Query,
    moments.schema.Query,
    payments.schema.Query,
    gifts.schema.Query,
    purchase.schema.Query,
    stock_image.schema.Query,
    reports.schema.Query,
    graphene.ObjectType,
):
    users = graphene.List(UserType, name=graphene.String(required=False))
    user = graphene.Field(UserType, id=graphene.String(required=True))
    translate_text = graphene.Field(Translation, sentence=graphene.String(required=True), target_language=graphene.String(required=True))

    random_users = graphene.Field(
        UserSearchAndPermissionType,
        interested_in=graphene.Int(),
        min_height=graphene.Int(),
        max_height=graphene.Int(),
        gender=graphene.Int(),
        id=graphene.String(),
        start=graphene.Int(),
        limit=graphene.Int(),
        min_age=graphene.Int(),
        max_age=graphene.Int(),
        latitude=graphene.Float(),
        longitude=graphene.Float(),
        family_plan=graphene.Int(),
        max_distance=graphene.Int(),
        politics=graphene.Int(),
        religious=graphene.Int(),
        zodiacSign=graphene.Int(),
        search_key=graphene.String(),
        address=graphene.String(),
        auto_deduct_coin=graphene.Int(),
        description="Search users based on their age, interest, height or gender",
    )
    popular_users = graphene.Field(
        UserSearchAndPermissionType,
        interested_in=graphene.Int(),
        min_height=graphene.Int(),
        max_height=graphene.Int(),
        gender=graphene.Int(),
        id=graphene.String(),
        start=graphene.Int(),
        limit=graphene.Int(),
        min_age=graphene.Int(),
        max_age=graphene.Int(),
        latitude=graphene.Float(),
        longitude=graphene.Float(),
        family_plan=graphene.Int(),
        max_distance=graphene.Int(),
        politics=graphene.Int(),
        religious=graphene.Int(),
        zodiacSign=graphene.Int(),
        search_key=graphene.String(),
        auto_deduct_coin=graphene.Int(),
        description="Search users based on their age, interest, height or gender",
    )
    most_active_users = graphene.Field(
        UserSearchAndPermissionType,
        interested_in=graphene.Int(),
        min_height=graphene.Int(),
        max_height=graphene.Int(),
        gender=graphene.Int(),
        id=graphene.String(),
        start=graphene.Int(),
        limit=graphene.Int(),
        min_age=graphene.Int(),
        max_age=graphene.Int(),
        latitude=graphene.Float(),
        longitude=graphene.Float(),
        family_plan=graphene.Int(),
        max_distance=graphene.Int(),
        politics=graphene.Int(),
        religious=graphene.Int(),
        zodiacSign=graphene.Int(),
        search_key=graphene.String(),
        auto_deduct_coin=graphene.Int(),
        description="Search users based on their age, interest, height or gender",
    )

    new_users = graphene.List(UserType)

    attr_translation = graphene.List(
        attrTranslationType,
        attr_names=graphene.List(graphene.String, required=True)
    )

    def resolve_translate_text(self, info, sentence, target_language):
        translation = translator.translate(sentence, dest=target_language)
        return Translation(text=sentence, translated_text=translation.text, language=translation.dest)

    def resolve_users(self, info, name=None):
        blocked = info.context.user.blockedUsers.all().values_list("id", flat=True)
        users = get_user_model().objects.filter(
            Q(social_auth__isnull=False) | Q(social_auth__isnull=True)
        ).exclude(
            id__in=blocked
        ).exclude(
            roles__in=UserRole.objects.filter(
                role__in=[UserRole.ROLE_CHATTER, UserRole.ROLE_ADMIN, UserRole.ROLE_SUPER_ADMIN]
            )
        ).exclude(is_deleted=True)

        if name:
            blocked_by = info.context.user.blocked_by.all().values_list("id", flat=True)
            users = users.filter(fullName__icontains=name).exclude(id__in=blocked_by)

        return users

    @staticmethod
    def resolve_user(self, info, **kwargs):
        id = kwargs.get("id")
        if not id:
            raise Exception(translate_error_message(
                info.context.user, "id is a required parameter"))
        try:
            user_obj = get_user_model().objects.get(id=id)
            return user_obj
        except User.DoesNotExist as e:
            raise Exception(translate_error_message(
                info.context.user, "User doesn't exists.")) from e

    @staticmethod
    def resolve_random_users(self, info, **kwargs):
        interest = kwargs.get("interested_in")
        max_age = kwargs.get("max_age")
        min_age = kwargs.get("min_age")
        max_height = kwargs.get("max_height")
        min_height = kwargs.get("min_height")
        gender = kwargs.get("gender")
        userid = kwargs.get("id")
        start = kwargs.get("start")
        limit = kwargs.get("limit")
        latitude = kwargs.get("latitude")
        longitude = kwargs.get("longitude")
        search_key = kwargs.get("search_key")
        family_plan = kwargs.get("family_plan")
        politics = kwargs.get("politics")
        religious = kwargs.get("religious")
        zodiacSign = kwargs.get("zodiacSign")
        max_distance = kwargs.get("max_distance")
        address = kwargs.get("address")
        auto_deduct_coin = kwargs.get("auto_deduct_coin")

        skip_users = info.context.user.blockedUsers.all().values_list("id", flat=True) or []
        skip_users.append(info.context.user.id)
        res = get_user_model().objects.all().exclude(id__in=skip_users).exclude(is_deleted=True)

        if interest:
            users = get_user_model().objects.all()
            filtered_users = [
                user.id for user in users if interest in user.interestedIn_display
            ]
            filtered_users = list(set(filtered_users))
            res = res.filter(id__in=filtered_users)

        if address:
            res = res.filter(address__contains=address)
        if userid:
            res = res.filter(~Q(id=userid))

        if family_plan:
            res = res.filter(familyPlans=family_plan)

        if politics:
            res = res.filter(politics=politics)

        if religious:
            res = res.filter(religion=religious)

        if zodiacSign:
            res = res.filter(zodiacSign=zodiacSign)

        if search_key and search_key != "":
            res = res.filter(fullName__contains=search_key)

        if max_distance and latitude and longitude:
            base_location = float(latitude), float(longitude)
            within_vicinity = []
            for user in res:
                if "," not in user.location:
                    continue

                user_location = tuple(map(float, user.location.split(",")))
                if not user_location:
                    continue

                if (
                    geopy.distance.distance(base_location, user_location).miles
                    <= max_distance
                ):
                    user.distance = str(
                        int(geopy.distance.distance(
                            base_location, user_location).miles)
                    )
                    user.save()
                    within_vicinity.append(user.id)
            if within_vicinity:
                res = res.filter(id__in=within_vicinity)
        else:
            for user in res:
                user.distance = ""
                user.save()

        if max_age is not None or min_age is not None:
            if max_age is None:
                max_age = Age.objects.last().age
            if min_age is None:
                min_age = Age.objects.first().age
            res = res.filter(age__age__range=(min_age, max_age))

        if max_height is not None or min_height is not None:
            if max_height is None:
                max_height = Height.objects.last().height
            if min_height is None:
                min_height = Height.objects.first().height

            res = res.filter(height__height__range=(min_height, max_height))

        if gender in [0,1,2]:
            res = res.filter(gender=gender)

        # order the result if the settings is enabled
        if is_feature_enabled(USER_ADVANCE_SORTING_FEATURE):
            now = timezone.now()
            res = res.annotate(
                current_subscription=Coalesce(
                    Subquery(
                        PackagePurchase.objects.filter(
                            user=OuterRef('id'), is_active=True,
                            starts_at__lte=now, ends_at__gte=now,
                            renewed_at__isnull=True
                        ).values('package_id')
                    ),
                    Value(0)
                ),
                user_role=F("roles__id") % MODERATOR_ID
            )
            res = res.order_by('user_role', '-current_subscription', '-purchase_coins')
        else:
            res = res.annotate(user_role=F("roles__id") % MODERATOR_ID)
            res = res.order_by('user_role')

        res = res.annotate(user_role=F("roles__role"))
        permission = "RANDOM_SEARCHED_USER_RESULTS_LIMIT"

        has_permision = get_user_search_permission(
            permission, info.context.user)
        coins_to_unlock = 0

        permission_obj = Permission.objects.filter(name=permission).first()
        free_limit = permission_obj.user_free_limit
        unlocked_limit = permission_obj.user_unlocked_result_limit
        res = res.exclude(
            roles__in=UserRole.objects.filter(
                role__in=[UserRole.ROLE_CHATTER, UserRole.ROLE_ADMIN, UserRole.ROLE_SUPER_ADMIN]
            )
        )
        res = res[:(free_limit+unlocked_limit)]

        if not has_permision:
            # check if user has paid for this permission within the last 24 hrs
            now = timezone.now()
            unlock_search_purchase = CoinSpendingHistory.objects.filter(
                user=info.context.user,
                description=permission,
                created_at__gte=now-timedelta(days=1)
            )

            if unlock_search_purchase.count() == 0:
                coins = CoinSettings.objects.filter(method=permission).first()
                coins_for_region = CoinSettingsForRegion.objects.filter(
                    coinsettings=coins, region=info.context.user.get_coinsettings_region()
                )
                if coins_for_region.count():
                    coins = coins_for_region.first()

                if auto_deduct_coin and coins and coins.coins_needed > 0:
                    info.context.user.deductCoins(
                        coins.coins_needed, permission)
                    info.context.user.save()
                    has_permision = True
                else:
                    if coins:
                        coins_to_unlock = coins.coins_needed
            else:
                has_permision = True

        if start:
            res = res[start:]

        if limit:
            res = res[:limit]

        return UserSearchAndPermissionType(
            user=res,
            my_permission=permissionType(
                has_permission=has_permision,
                coins_to_unlock=coins_to_unlock,
                free_user_limit=free_limit
            )
        )

    @staticmethod
    def resolve_popular_users(self, info, **kwargs):
        interest = kwargs.get("interested_in")
        max_age = kwargs.get("max_age")
        min_age = kwargs.get("min_age")
        max_height = kwargs.get("max_height")
        min_height = kwargs.get("min_height")
        gender = kwargs.get("gender")
        userid = kwargs.get("id")
        start = kwargs.get("start")
        limit = kwargs.get("limit")
        latitude = kwargs.get("latitude")
        longitude = kwargs.get("longitude")
        search_key = kwargs.get("search_key")
        family_plan = kwargs.get("family_plan")
        politics = kwargs.get("politics")
        religious = kwargs.get("religious")
        zodiacSign = kwargs.get("zodiacSign")
        max_distance = kwargs.get("max_distance")
        auto_deduct_coin = kwargs.get("auto_deduct_coin")

        blocked = info.context.user.blockedUsers.all().values_list("id", flat=True)
        res = get_user_model().objects.all().exclude(id__in=blocked).exclude(is_deleted=True)

        res = res.annotate(
            visitor_count=Count('user_visiting', distinct=True),
            follower_count=Count('user_following', distinct=True),
            popularity=F('visitor_count')+F('follower_count'),
            user_role=F("roles__id") % MODERATOR_ID
        )
        res = res.order_by('-popularity')

        if interest:
            users = (
                get_user_model().objects.all()
            )
            filtered_users = []
            for user in users:
                if interest in user.interestedIn_display:
                    filtered_users.append(user.id)

            filtered_users = list(set(filtered_users))
            res = res.filter(id__in=filtered_users)

        if latitude:
            res = res.filter(location__contains=latitude)
        if userid:
            res = res.filter(~Q(id=userid))
        if longitude:
            res = res.filter(location__contains=longitude)

        if family_plan:
            res = res.filter(familyPlans=family_plan)

        if politics:
            res = res.filter(politics=politics)

        if religious:
            res = res.filter(religion=religious)

        if zodiacSign:
            res = res.filter(zodiacSign=zodiacSign)

        if search_key and search_key != "":
            res = res.filter(fullName__contains=search_key)

        if max_distance and latitude and longitude:
            base_location = float(latitude), float(longitude)
            within_vicinity = []
            for user in res:
                user_location = tuple(map(float, user.location.split(",")))
                if not user_location:
                    continue

                if (
                    geopy.distance.distance(base_location, user_location).miles
                    <= max_distance
                ):
                    within_vicinity.append(user.id)

            if within_vicinity:
                res = res.filter(id__in=within_vicinity)

        if max_age is not None or min_age is not None:
            if max_age is None:
                max_age = Age.objects.last().age
            if min_age is None:
                min_age = Age.objects.first().age

            res = res.filter(age__age__range=(min_age, max_age))

        if max_height is not None or min_height is not None:
            if max_height is None:
                max_height = Height.objects.last().height
            if min_height is None:
                min_height = Height.objects.first().height

            res = res.filter(height__height__range=(min_height, max_height))

        if gender in [0,1,2]:
            res = res.filter(gender=gender)

        # order the result if the settings is enabled
        if is_feature_enabled(USER_ADVANCE_SORTING_FEATURE):
            now = timezone.now()
            res = res.annotate(
                current_subscription=Coalesce(
                    Subquery(
                        PackagePurchase.objects.filter(
                            user=OuterRef('id'), is_active=True,
                            starts_at__lte=now, ends_at__gte=now,
                            renewed_at__isnull=True
                        ).values('package_id')
                    ),
                    Value(0)
                )
            )
            res = res.order_by('user_role','-current_subscription', '-purchase_coins')
        else:
            res = res.order_by('user_role','-popularity')

        permission = "POPULAR_SEARCHED_USER_RESULTS_LIMIT"

        has_permision = get_user_search_permission(
            permission, info.context.user)
        coins_to_unlock = 0

        permission_obj = Permission.objects.filter(name=permission).first()
        free_limit = permission_obj.user_free_limit
        unlocked_limit = permission_obj.user_unlocked_result_limit
        res = res.exclude(
            roles__in=UserRole.objects.filter(
                role__in=[UserRole.ROLE_CHATTER, UserRole.ROLE_ADMIN, UserRole.ROLE_SUPER_ADMIN]
            )
        )
        res = res[:(free_limit+unlocked_limit)]

        if not has_permision:
            # check if user has paid for this permission within the last 24 hrs
            now = timezone.now()
            unlock_search_purchase = CoinSpendingHistory.objects.filter(
                user=info.context.user,
                description=permission,
                created_at__gte=now-timedelta(days=1)
            )

            if unlock_search_purchase.count() == 0:
                coins = CoinSettings.objects.filter(method=permission).first()
                coins_for_region = CoinSettingsForRegion.objects.filter(
                    coinsettings=coins, region=info.context.user.get_coinsettings_region()
                )
                if coins_for_region.count():
                    coins = coins_for_region.first()

                if auto_deduct_coin and coins and coins.coins_needed > 0:
                    info.context.user.deductCoins(
                        coins.coins_needed, permission)
                    info.context.user.save()
                    has_permision = True
                else:
                    if coins:
                        coins_to_unlock = coins.coins_needed
            else:
                has_permision = True

        if start:
            res = res[start:]

        if limit:
            res = res[:limit]

        return UserSearchAndPermissionType(
            user=res,
            my_permission=permissionType(
                has_permission=has_permision,
                coins_to_unlock=coins_to_unlock,
                free_user_limit=free_limit
            )
        )

    @staticmethod
    def resolve_most_active_users(self, info, **kwargs):
        interest = kwargs.get("interested_in")
        max_age = kwargs.get("max_age")
        min_age = kwargs.get("min_age")
        max_height = kwargs.get("max_height")
        min_height = kwargs.get("min_height")
        gender = kwargs.get("gender")
        userid = kwargs.get("id")
        start = kwargs.get("start")
        limit = kwargs.get("limit")
        latitude = kwargs.get("latitude")
        longitude = kwargs.get("longitude")
        search_key = kwargs.get("search_key")
        family_plan = kwargs.get("family_plan")
        politics = kwargs.get("politics")
        religious = kwargs.get("religious")
        zodiacSign = kwargs.get("zodiacSign")
        max_distance = kwargs.get("max_distance")
        auto_deduct_coin = kwargs.get("auto_deduct_coin")

        blocked = info.context.user.blockedUsers.all().values_list("id", flat=True)
        res = get_user_model().objects.all().exclude(id__in=blocked).exclude(is_deleted=True)

        res = res.annotate(
            chat_message_count=Count('Sender', distinct=True),
            story_count=Count('story', distinct=True),
            follow_count=Count('user_follower', distinct=True),
            visit_count=Count('user_visitor', distinct=True),
            user_role=F("roles__id") % MODERATOR_ID
        )

        res = res.annotate(activity_count=F('chat_message_count') +
                           F('story_count') +
                           F('follow_count')+F('visit_count')
                           )
        res = res.order_by('user_role', '-isOnline', '-activity_count')

        if interest:
            users = get_user_model().objects.all()
            filtered_users = []
            for user in users:
                if interest in user.interestedIn_display:
                    filtered_users.append(user.id)

            filtered_users = list(set(filtered_users))
            res = res.filter(id__in=filtered_users)

        if latitude:
            res = res.filter(location__contains=latitude)
        if userid:
            res = res.filter(~Q(id=userid))
        if longitude:
            res = res.filter(location__contains=longitude)

        if family_plan:
            res = res.filter(familyPlans=family_plan)

        if politics:
            res = res.filter(politics=politics)

        if religious:
            res = res.filter(religion=religious)

        if zodiacSign:
            res = res.filter(zodiacSign=zodiacSign)

        if search_key and search_key != "":
            res = res.filter(fullName__contains=search_key)

        if max_distance and latitude and longitude:
            base_location = float(latitude), float(longitude)
            within_vicinity = []
            for user in res:
                user_location = tuple(map(float, user.location.split(",")))
                if not user_location:
                    continue
                if (
                    geopy.distance.distance(base_location, user_location).miles
                    <= max_distance
                ):
                    within_vicinity.append(user.id)
            if within_vicinity:
                res = res.filter(id__in=within_vicinity)

        if max_age is not None or min_age is not None:
            if max_age is None:
                max_age = Age.objects.last().age
            if min_age is None:
                min_age = Age.objects.first().age

            res = res.filter(age__age__range=(min_age, max_age))

        if max_height is not None or min_height is not None:
            if max_height is None:
                max_height = Height.objects.last().height
            if min_height is None:
                min_height = Height.objects.first().height

            res = res.filter(height__height__range=(min_height, max_height))
        res = res.filter(isOnline=True)

        if gender in [0,1,2]:
            res = res.filter(gender=gender)

        # order the result if the settings is enabled
        if is_feature_enabled(USER_ADVANCE_SORTING_FEATURE):
            now = timezone.now()
            res = res.annotate(
                current_subscription=Coalesce(
                    Subquery(
                        PackagePurchase.objects.filter(
                            user=OuterRef('id'), is_active=True,
                            starts_at__lte=now, ends_at__gte=now,
                            renewed_at__isnull=True
                        ).values('package_id')
                    ),
                    Value(0)
                )
            )
            res = res.order_by('user_role', '-current_subscription', '-purchase_coins')

        permission = "MOST_ACTIVE_SEARCHED_USER_RESULTS_LIMIT"

        has_permision = get_user_search_permission(
            permission, info.context.user)
        coins_to_unlock = 0

        permission_obj = Permission.objects.filter(name=permission).first()
        free_limit = permission_obj.user_free_limit
        unlocked_limit = permission_obj.user_unlocked_result_limit
        res = res.exclude(
            roles__in=UserRole.objects.filter(
                role__in=[UserRole.ROLE_CHATTER, UserRole.ROLE_ADMIN, UserRole.ROLE_SUPER_ADMIN]
            )
        )
        res = res[:(free_limit+unlocked_limit)]

        if not has_permision:
            # check if user has paid for this permission within the last 24 hrs
            now = timezone.now()
            unlock_search_purchase = CoinSpendingHistory.objects.filter(
                user=info.context.user,
                description=permission,
                created_at__gte=now-timedelta(days=1)
            )

            if unlock_search_purchase.count() == 0:
                coins = CoinSettings.objects.filter(method=permission).first()
                coins_for_region = CoinSettingsForRegion.objects.filter(
                    coinsettings=coins, region=info.context.user.get_coinsettings_region()
                )
                if coins_for_region.count():
                    coins = coins_for_region.first()

                if auto_deduct_coin and coins and coins.coins_needed > 0:
                    info.context.user.deductCoins(
                        coins.coins_needed, permission)
                    info.context.user.save()
                    has_permision = True
                else:
                    if coins:
                        coins_to_unlock = coins.coins_needed
            else:
                has_permision = True

        if start:
            res = res[start:]

        if limit:
            res = res[:limit]

        return UserSearchAndPermissionType(
            user=res,
            my_permission=permissionType(
                has_permission=has_permision,
                coins_to_unlock=coins_to_unlock,
                free_user_limit=free_limit
            )
        )

    def resolve_new_users(self, info, **kwargs):
        days = Settings.get_setting(key="new_users_num_of_days", default=1)
        hours = int(days) * 24
        delta = datetime.now() - timedelta(hours=hours)

        return (
            get_user_model()
            .objects.filter(created_at__gte=delta)
            .exclude(
                id=info.context.user.id,
                roles__role__in=["CHATTER", "ADMIN", "MODERATOR"],
            )
        )

    def resolve_attr_translation(self, info, **kwargs):
        attr_names = kwargs.get("attr_names")
        all_translations = []
        attr_names_flag = {}

        name_translations = UserProfileTranlations.objects.filter(
            name__in=attr_names)

        for attr_name in attr_names:
            attr_names_flag[attr_name] = False

        for name_translation in name_translations:
            name = name_translation.name
            name_translated = getattr(
                name_translation, translated_field_name(info.context.user, "name"))
            attr_names_flag[name] = True
            all_translations.append(attrTranslationType(
                name=name, name_translated=name_translated))

        for attr_name in attr_names:
            if not attr_names_flag[attr_name]:
                all_translations.append(attrTranslationType(
                    name=attr_name, name_translated=""))

        return all_translations


class ProfileViewMiddleware:
    def resolve(self, next_middleware, root, info, **args):
        # Call the next middleware in the chain
        result = next_middleware(root, info, **args)
        #print("in the middleware ===========================")
        # Get the authenticated user and the viewed user
        visitor = info.context.user
        visiting = result

        # Create the new profile view
        if viewer.is_authenticated and viewed_user != viewer:
            #print("createedddd user===============================")
            # ProfileView.objects.create(viewer=viewer, viewed_user=viewed_user)
            pass
        # Return the result
        return result


class Subscription(
    chat.schema.Subscription,
    moments.schema.Subscription,
    user.schema.Subscription,
    payments.schema.Subscription,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation,
                         subscription=Subscription)


class MyGraphqlWsConsumer(channels_graphql_ws.GraphqlWsConsumer):
    schema = schema

    async def on_connect(self, payload):
        self.scope["user"] = await channels.auth.get_user(self.scope)
