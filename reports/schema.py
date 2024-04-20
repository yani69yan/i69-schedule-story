import datetime

import graphene
import requests
from dj_rest_auth.serializers import TokenSerializer
from dj_rest_auth.utils import default_create_token
from django.contrib.auth import get_user_model
from graphene_django import DjangoObjectType
from requests_oauthlib import OAuth1
from rest_framework.authtoken.models import Token
from social.apps.django_app.default.models import UserSocialAuth

from reports.constants import DELETED_ACCOUNT_MESSAGE_EN
from reports.models import GoogleAuth, Reported_Users, SocialAuthDetail
from user.models import User, settings
from user.utils import translate_error_message


def get_token(user):
    if not user:
        return ""
    token = default_create_token(Token, user, TokenSerializer)
    return token.key


class reportResponseObj(graphene.ObjectType):
    id = graphene.String()


class reportUser(graphene.Mutation):
    class Arguments:
        reporter = graphene.String(required=True)
        reportee = graphene.String(required=True)
        reason = graphene.String(required=True)

    Output = reportResponseObj

    def mutate(self, info, reporter, reportee, reason):
        User = get_user_model()

        try:
            reporter_user = User.objects.get(id=reporter)
            reportee_user = User.objects.get(id=reportee)
        except Exception:
            raise Exception(translate_error_message(info.context.user, "User does not exist"))

        if reporter_user == reportee_user:
            raise Exception(translate_error_message(info.context.user, "You can not report yourself"))

        report = Reported_Users.objects.create(
            reporter=reporter_user, reportee=reportee_user, reason=reason
        )
        print(Reported_Users.id)
        return reportResponseObj(id=report.id)


class googleAuthResponse(graphene.ObjectType):
    email = graphene.String()
    is_new = graphene.Boolean()
    id = graphene.String()
    token = graphene.String()
    username = graphene.String()


class twitterAuthResponse(graphene.ObjectType):
    twitter = graphene.String()
    username = graphene.String()
    is_new = graphene.Boolean()
    id = graphene.String()
    token = graphene.String()


class FacebookAuthResponse(graphene.ObjectType):
    twitter = graphene.String()
    username = graphene.String()
    is_new = graphene.Boolean()
    id = graphene.String()
    token = graphene.String()


def check_is_new(user: User):
    """
    Check whether a user is not properly initialized
    """
    if (
        user.age == None
        or user.fullName == ""
        or user.height == None
        or user.avatar_photos.all().count() == 0
    ):
        return True
    return False


class SocialAuth(graphene.Mutation):
    class Arguments:
        access_token = graphene.String(required=True)
        provider = graphene.String(required=True)
        access_verifier = graphene.String(default_value="")

    Output = googleAuthResponse

    def mutate(self, info, access_token, provider, access_verifier=""):
        try:

            if "google" in provider.lower():
                idinfo = requests.get(
                    f"https://oauth2.googleapis.com/tokeninfo?id_token={access_token}"
                )
                idinfo = idinfo.json()
                if idinfo.get("error") == "invalid_token":
                    return Exception(translate_error_message(info.context.user, "Invalid Token"))

            if "facebook" in provider.lower():
                idinfo = requests.get(
                    f"https://graph.facebook.com/me?fields=name,email&access_token={access_token}"
                )
                idinfo = idinfo.json()
                if idinfo.get("error") == "invalid_token":
                    return Exception(translate_error_message(info.context.user, "Invalid Token"))

                facebook_id = idinfo.get("id")
                if not facebook_id:
                    return Exception(translate_error_message(info.context.user, "Invalid token"))

                email = idinfo.get("email", f"{facebook_id}_fb@facebook.com")
                idinfo["email"] = email
                user, is_new = get_user_model().objects.get_or_create(
                    username=email.replace("@", "_"),
                    defaults={
                        "password": "",
                        "fullName": idinfo["name"],
                        "email": email,
                        "username": email.replace("@", "_"),
                        "facebook_id": facebook_id,
                    },
                )
                if user and user.is_deleted:
                    # Before login messages should be in English only so that Mobile App can translate according to device language.
                    return Exception(DELETED_ACCOUNT_MESSAGE_EN)


                user.facebook_id = user.facebook_id or facebook_id
                user.last_login = datetime.datetime.now()
                user.save()

                if is_new:
                    social_auth, _ = UserSocialAuth.objects.get_or_create(
                        user_id=user.id,
                        defaults={
                            "provider": provider.lower(),
                            "uid": facebook_id,
                            "user_id": user.id,
                            "extra_data": "",
                        },
                    )
                    social_auth.save()

                return googleAuthResponse(
                    email=idinfo["email"],
                    is_new=is_new,
                    id=user.id,
                    token=get_token(user),
                    username=idinfo["email"].replace("@", "_"),
                )

            if "apple" in provider.lower():
                if access_verifier == "":
                    access_verifier_check = UserSocialAuth.objects.filter(
                        extra_data=access_token
                    ).first()
                    if access_verifier_check:
                        access_verifier = access_verifier_check.uid
                    else:
                        return Exception(translate_error_message(info.context.user, "Email is required for first sign in."))

                user = get_user_model().objects.filter(email=access_verifier).first()
                if user:
                    if user.is_deleted:
                        # Before login messages should be in English only so that Mobile App can translate according to device language.
                        return Exception(DELETED_ACCOUNT_MESSAGE_EN)

                    is_new = check_is_new(user)
                else:
                    user, _ = get_user_model().objects.get_or_create(
                        email=access_verifier,
                        defaults={
                            "password": "",
                            "fullName": "",
                            "email": access_verifier,
                            "username": access_verifier.replace("@", "_"),
                        },
                    )
                    if user and user.is_deleted:
                        # Before login messages should be in English only so that Mobile App can translate according to device language.
                        return Exception(DELETED_ACCOUNT_MESSAGE_EN)

                    user.last_login = datetime.datetime.now()
                    user.save()

                    socialAuth, _ = UserSocialAuth.objects.get_or_create(
                        user_id=user.id,
                        defaults={
                            "provider": provider.lower(),
                            "uid": access_verifier,
                            "user_id": user.id,
                            "extra_data": access_token,
                        },
                    )
                    socialAuth.save()

                    is_new = True

                return googleAuthResponse(
                    email=access_verifier,
                    is_new=is_new,
                    id=user.id,
                    token=get_token(user),
                    username=access_verifier.replace("@", "_"),
                )

            if "twitter" in provider.lower():
                oauth = OAuth1(
                    settings.SOCIAL_AUTH_TWITTER_KEY,
                    client_secret=settings.SOCIAL_AUTH_TWITTER_SECRET,
                    resource_owner_key=access_token,
                    verifier=access_verifier,
                )
                res = requests.post(
                    f"https://api.twitter.com/oauth/access_token", auth=oauth
                )
                res_split = res.text.split("&")
                if len(res_split) >= 4:
                    user_id = res_split[2].split("=")[1] if len(res_split) > 2 else None
                    user_name = (
                        res_split[3].split("=")[1] if len(res_split) > 3 else None
                    )
                else:
                    return Exception(res.text)

                if not any([user_id, user_name]):
                    return Exception(translate_error_message(info.context.user, "Invalied token"))
                else:
                    try:
                        user = get_user_model().objects.get(twitter=user_id)
                        if user and user.is_deleted:
                            # Before login messages should be in English only so that Mobile App can translate according to device language.
                            raise Exception(DELETED_ACCOUNT_MESSAGE_EN)

                        is_new = check_is_new(user)
                    except:
                        user, _ = get_user_model().objects.get_or_create(
                            twitter=user_id,
                            defaults={
                                "password": "",
                                "fullName": user_name,
                                "email": user_id + "@twitter.com",
                                "username": user_name + "_twitter",
                            },
                        )
                        if user and user.is_deleted:
                            # Before login messages should be in English only so that Mobile App can translate according to device language.
                            return Exception(DELETED_ACCOUNT_MESSAGE_EN)

                        user.last_login = datetime.datetime.now()
                        user.save()
                        is_new = True

                        socialAuth, _ = UserSocialAuth.objects.get_or_create(
                            user_id=user.id,
                            defaults={
                                "provider": provider.lower(),
                                "uid": user_id,
                                "user_id": user.id,
                                "extra_data": "",
                            },
                        )
                        socialAuth.save()

                    return twitterAuthResponse(
                        twitter=user_id,
                        is_new=is_new,
                        id=user.id,
                        token=get_token(user),
                        username=user.username,
                    )

            # Provider: Google
            user = get_user_model().objects.filter(email=idinfo["email"]).first()
            if user:
                if user.is_deleted:
                    # Before login messages should be in English only so that Mobile App can translate according to device language.
                    raise Exception(DELETED_ACCOUNT_MESSAGE_EN)

                is_new = check_is_new(user)
                user.last_login = datetime.datetime.now()
                user.save()
            else:
                user, _ = get_user_model().objects.get_or_create(
                    email=idinfo["email"],
                    defaults={
                        "password": "",
                        "fullName": idinfo["name"],
                        "email": idinfo["email"],
                        "username": idinfo["email"].replace("@", "_"),
                    },
                )
                if user.is_deleted:
                    # Before login messages should be in English only so that Mobile App can translate according to device language.
                    raise Exception(DELETED_ACCOUNT_MESSAGE_EN)

                user.last_login = datetime.datetime.now()
                user.save()

                socialAuth, _ = UserSocialAuth.objects.get_or_create(
                    user_id=user.id,
                    defaults={
                        "provider": provider.lower(),
                        "uid": idinfo["email"],
                        "user_id": user.id,
                        "extra_data": "",
                    },
                )
                socialAuth.save()

                is_new = True

                g_auth = GoogleAuth.objects.create(
                    email=idinfo["email"], sub=idinfo.get("sub")
                )
                g_auth.save()

            return googleAuthResponse(
                email=idinfo["email"],
                is_new=is_new,
                id=user.id,
                token=get_token(user),
                username=idinfo["email"].replace("@", "_"),
            )
        except ValueError:
            Exception(translate_error_message(info.context.user, "Invalid Token"))


class SocialAuthUpdateResponse(graphene.ObjectType):
    success = graphene.Boolean()
    message = graphene.String()


class SocialAuthDetailType(DjangoObjectType):
    class Meta:
        model = SocialAuthDetail
        fields = "__all__"


class SocialAuthStatusEnum(graphene.Enum):
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class ADDSocialAuthMutation(graphene.Mutation):
    class Arguments:
        provider = graphene.String(required=True)
        status = SocialAuthStatusEnum(required=True)

    social_auth = graphene.Field(SocialAuthDetailType)

    @classmethod
    def mutate(cls, root, info, provider, status):
        if provider.lower() not in ['google', 'facebook', 'twitter', 'apple']:
            raise Exception(translate_error_message(info.context.user, "Platform unknown!"))

        new_report = SocialAuthDetail(provider=provider, status=status)
        new_report.save()

        return ADDSocialAuthMutation(social_auth=new_report)

class UpdateSocialAuthMutation(graphene.Mutation):
    Output = SocialAuthUpdateResponse

    class Arguments:
        id = graphene.Int(required=True)
        status = SocialAuthStatusEnum(required=True)

    def mutate(self, info, id, status):
        try:
            social_auth = SocialAuthDetail.objects.get(id=id)
            social_auth.status = status
            social_auth.save()
            return SocialAuthUpdateResponse(
                success=True, message=translate_error_message(info.context.user, "Social Auth Instance Updated Successfully!")
            )
        except:
            return SocialAuthUpdateResponse(success=False, message=translate_error_message(info.context.user, "Social Auth Instance not found!"))


class DeleteSocialAuthMutation(graphene.Mutation):

    id = graphene.Int()
    success = graphene.String()

    class Arguments:
        id = graphene.ID()

    @classmethod
    def mutate(cls, root, info, id):
        try:
            delete_social = SocialAuthDetail.objects.get(id=id)
            delete_social.delete()
            return DeleteSocialAuthMutation(success="deleted successfully", id=id)

        except Exception as e:
            raise Exception(translate_error_message(info.context.user, "invalid social auth instance id"))


class Mutation(graphene.ObjectType):
    social_auth = SocialAuth.Field()
    reportUser = reportUser.Field()
    create_social_auth_detail = ADDSocialAuthMutation.Field()
    update_social_auth_detail = UpdateSocialAuthMutation.Field()
    delete_social_auth_detail = DeleteSocialAuthMutation.Field()

class Query(graphene.ObjectType):
    all_social_auth_status = graphene.List(SocialAuthDetailType)

    def resolve_all_social_auth_status(self, info, **kwargs):
        return SocialAuthDetail.objects.all().order_by("-timestamp")
