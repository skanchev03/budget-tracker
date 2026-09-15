from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import Account
from apps.core.models import ExchangeRate
from apps.transactions.models import Transaction, Transfer


ZERO = Decimal("0")
MONEY_QUANTIZER = Decimal("0.0001")


def get_exchange_rate(
    *,
    from_currency,
    to_currency,
    valid_at=None,
):
    """
    Find the latest exchange rate available at or before valid_at.

    If a direct rate does not exist, try the inverse rate.
    """

    if from_currency.pk == to_currency.pk:
        return Decimal("1")

    if valid_at is None:
        valid_at = timezone.now()

    direct_rate = (
        ExchangeRate.objects
        .filter(
            from_currency=from_currency,
            to_currency=to_currency,
            valid_at__lte=valid_at,
        )
        .order_by("-valid_at", "-id")
        .first()
    )

    if direct_rate is not None:
        return direct_rate.rate

    inverse_rate = (
        ExchangeRate.objects
        .filter(
            from_currency=to_currency,
            to_currency=from_currency,
            valid_at__lte=valid_at,
        )
        .order_by("-valid_at", "-id")
        .first()
    )

    if inverse_rate is not None:
        return Decimal("1") / inverse_rate.rate

    return None


def convert_amount(
    *,
    amount,
    from_currency,
    to_currency,
    valid_at=None,
):
    """
    Convert an amount to another currency.

    Returns None when no exchange rate is available.
    """

    amount = Decimal(amount)

    if from_currency.pk == to_currency.pk:
        return amount

    rate = get_exchange_rate(
        from_currency=from_currency,
        to_currency=to_currency,
        valid_at=valid_at,
    )

    if rate is None:
        return None

    return amount * rate


def _convert_and_round(
    *,
    amount,
    from_currency,
    to_currency,
    valid_at=None,
):
    """
    Convert an amount and round it to four decimal places.
    """

    converted = convert_amount(
        amount=amount,
        from_currency=from_currency,
        to_currency=to_currency,
        valid_at=valid_at,
    )

    if converted is None:
        return None

    return converted.quantize(
        MONEY_QUANTIZER,
        rounding=ROUND_HALF_UP,
    )


def get_account_balances_in_base_currency(user):
    """
    Return active account balances converted to the user's
    base currency.
    """

    base_currency = user.base_currency

    accounts = (
        Account.objects
        .filter(
            user=user,
            is_active=True,
        )
        .select_related("currency")
        .order_by("display_order", "name")
    )

    result = []

    for account in accounts:

        converted_balance = _convert_and_round(
            amount=account.current_balance,
            from_currency=account.currency,
            to_currency=base_currency,
        )

        result.append(
            {
                "account": account,
                "currency": account.currency,
                "original_balance": account.current_balance,
                "converted_balance": converted_balance,
            }
        )

    return result


def get_total_balance(user):
    """
    Calculate total active account balance in the user's
    base currency.
    """

    account_balances = get_account_balances_in_base_currency(
        user,
    )

    total = ZERO
    missing_rates = []

    for item in account_balances:

        converted_balance = item["converted_balance"]

        if converted_balance is None:
            missing_rates.append(item["account"])
            continue

        total += converted_balance

    return {
        "total": total,
        "base_currency": user.base_currency,
        "account_balances": account_balances,
        "missing_rates": missing_rates,
    }


def get_dashboard_summary(user):
    """
    Calculate dashboard income, expenses and net cash flow
    in the user's base currency.

    Historical exchange rates are used according to each
    transaction's occurred_at timestamp.

    Transfers are excluded.
    """

    base_currency = user.base_currency

    transactions = (
        Transaction.objects
        .filter(user=user)
        .select_related("currency")
        .order_by("occurred_at", "id")
    )

    income = ZERO
    expenses = ZERO
    missing_rates = []

    for transaction in transactions:

        converted_amount = _convert_and_round(
            amount=transaction.amount,
            from_currency=transaction.currency,
            to_currency=base_currency,
            valid_at=transaction.occurred_at,
        )

        if converted_amount is None:
            missing_rates.append(transaction)
            continue

        if transaction.type == Transaction.INCOME:
            income += converted_amount

        elif transaction.type == Transaction.EXPENSE:
            expenses += converted_amount

    transfer_count = Transfer.objects.filter(
        user=user,
    ).count()

    account_count = Account.objects.filter(
        user=user,
        is_active=True,
    ).count()

    return {
        "accounts": (
            Account.objects
            .filter(
                user=user,
                is_active=True,
            )
            .select_related("currency")
        ),
        "account_count": account_count,
        "income": income,
        "expenses": expenses,
        "net_cash_flow": income - expenses,
        "transfer_count": transfer_count,
        "missing_transaction_rates": missing_rates,
    }


def get_recent_transactions(user, limit=10):
    """
    Return the user's most recent income and expense transactions.
    """

    return (
        Transaction.objects
        .filter(user=user)
        .select_related(
            "account",
            "category",
            "subcategory",
            "currency",
        )
        .order_by(
            "-occurred_at",
            "-id",
        )[:limit]
    )


def get_recent_transfers(user, limit=10):
    """
    Return the user's most recent transfers.
    """

    return (
        Transfer.objects
        .filter(user=user)
        .select_related(
            "from_account",
            "to_account",
            "from_currency",
            "to_currency",
        )
        .order_by(
            "-occurred_at",
            "-id",
        )[:limit]
    )


def get_expenses_by_category(user):
    """
    Calculate expenses grouped by category.

    Each expense is converted using the historical exchange
    rate valid at the transaction's occurred_at timestamp.
    """

    base_currency = user.base_currency

    transactions = (
        Transaction.objects
        .filter(
            user=user,
            type=Transaction.EXPENSE,
        )
        .select_related(
            "category",
            "currency",
        )
        .order_by(
            "category__name",
            "occurred_at",
            "id",
        )
    )

    categories = {}

    for transaction in transactions:

        converted_amount = _convert_and_round(
            amount=transaction.amount,
            from_currency=transaction.currency,
            to_currency=base_currency,
            valid_at=transaction.occurred_at,
        )

        if converted_amount is None:
            continue

        category_id = transaction.category_id

        if category_id not in categories:
            categories[category_id] = {
                "category_id": category_id,
                "category__name": transaction.category.name,
                "category__emoji": transaction.category.emoji,
                "total": ZERO,
            }

        categories[category_id]["total"] += converted_amount

    return sorted(
        categories.values(),
        key=lambda item: (
            -item["total"],
            item["category__name"],
        ),
    )


def get_monthly_income_expenses(user, months=12):
    """
    Returns income and expenses grouped by calendar month.

    Amounts are converted to the user's base currency using
    the exchange rate valid at the transaction's occurred_at time.
    """

    base_currency = user.base_currency

    today = timezone.localdate()
    current_month = today.replace(day=1)

    # Build the requested calendar months.
    month_list = []

    year = current_month.year
    month = current_month.month

    for _ in range(months):
        month_list.append((year, month))

        month -= 1

        if month == 0:
            month = 12
            year -= 1

    month_list.reverse()

    monthly_data = {}

    for year, month in month_list:
        month_key = f"{year:04d}-{month:02d}"

        monthly_data[month_key] = {
            "month": month_key,
            "label": f"{month:02d}/{year}",
            "income": ZERO,
            "expenses": ZERO,
        }

    first_year, first_month = month_list[0]

    start_date = timezone.datetime(
        first_year,
        first_month,
        1,
        tzinfo=timezone.get_current_timezone(),
    )

    transactions = (
        Transaction.objects
        .filter(
            user=user,
            occurred_at__gte=start_date,
        )
        .select_related("currency")
        .order_by("occurred_at", "id")
    )

    missing_rates = []

    for transaction in transactions:
        local_date = timezone.localtime(transaction.occurred_at)

        month_key = (
            f"{local_date.year:04d}-{local_date.month:02d}"
        )

        if month_key not in monthly_data:
            continue

        converted_amount = _convert_and_round(
            amount=transaction.amount,
            from_currency=transaction.currency,
            to_currency=base_currency,
            valid_at=transaction.occurred_at,
        )

        if converted_amount is None:
            missing_rates.append(transaction)
            continue

        if transaction.type == Transaction.INCOME:
            monthly_data[month_key]["income"] += converted_amount

        elif transaction.type == Transaction.EXPENSE:
            monthly_data[month_key]["expenses"] += converted_amount

    return {
        "months": list(monthly_data.values()),
        "missing_rates": missing_rates,
        "base_currency": base_currency,
    }