from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError
import redis
import logging


class Command(BaseCommand):
    help = "Checks Database and Redis connections"

    def handle(self, *args, **kwargs):
        db_conn = connections["default"]

        try:
            db_conn.cursor()
        except OperationalError:
            logging.getLogger('django').warning("Database connection failed")
        else:
            logging.getLogger('django').info("Database connection successfull")

        try:
            r = redis.StrictRedis.from_url("redis://i69_redis:y4pFPrDBeTLs6_ac@redis:6379/0")
            r.ping()
        except OperationalError:
            logging.getLogger('django').warning("Redis connection failed")
        else:
            logging.getLogger('django').info("Redis (Cache, Celery, and Channels) connection successfull")
