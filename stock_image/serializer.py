from django.contrib.auth import get_user_model
from graphene_django import DjangoObjectType

from .models import StockImage

User = get_user_model()


class StockImageType(DjangoObjectType):
    class Meta:
        model = StockImage
        fields = ["id", "file", "created_date"]

    def resolve_file(self, info):
        if self.file:
            return self.file.url
