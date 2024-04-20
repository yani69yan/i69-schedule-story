from dateutil.relativedelta import relativedelta
from django.utils import timezone

from purchase.models import PackagePurchase


payment_method_choices = [
    ("Gpay", "Gpay"),
    ("Stripe", "Stripe"),
    ("Boku", "Boku"),
    ("PayPal", "PayPal"),
]

package_plans_duration_timedeltas = {
    "PERWEEK": relativedelta(weeks=+1),
    "PERMONTH": relativedelta(months=+1),
    "PER3MONTH": relativedelta(months=+3),
    "PER6MONTH": relativedelta(months=+6),
    "PERYEAR": relativedelta(years=+1),
}

cancel_subscription_choices = [
    ("Yes", "Yes"),
    ("No", "No"),
]


def get_user_current_package(user):
    now = timezone.now()
    return PackagePurchase.objects.filter(
        user=user, is_active=True, starts_at__lte=now, ends_at__gte=now
    ).first()