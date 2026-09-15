from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.accounts.models import Account
from apps.core.models import Currency


@transaction.atomic
def create_account(
    *,
    user,
    name,
    emoji="💰",
    color="#3498DB",
    currency,
    opening_balance=0,
    display_order=0,
):
    if not Currency.objects.filter(pk=currency.pk).exists():
        raise ValueError("Invalid currency.")

    account = Account.objects.create(
        user=user,
        name=name,
        emoji=emoji,
        color=color,
        currency=currency,
        opening_balance=opening_balance,
        current_balance=opening_balance,
        display_order=display_order,
    )

    return account


def get_user_accounts(user):
    return Account.objects.filter(
        user=user,
        is_active=True,
    ).select_related("currency")


def get_user_account(*, user, account_id):
    account = (
        Account.objects
        .select_related("currency")
        .filter(
            pk=account_id,
            user=user,
        )
        .first()
    )

    if account is None:
        raise PermissionDenied(
            "You do not have permission to access this account."
        )

    return account


@transaction.atomic
def update_account(
    *,
    user,
    account_id,
    name=None,
    emoji=None,
    color=None,
    display_order=None,
    is_active=None,
):
    account = get_user_account(
        user=user,
        account_id=account_id,
    )

    if name is not None:
        account.name = name

    if emoji is not None:
        account.emoji = emoji

    if color is not None:
        account.color = color

    if display_order is not None:
        account.display_order = display_order

    if is_active is not None:
        account.is_active = is_active

    account.save()

    return account


@transaction.atomic
def delete_account(*, user, account_id):
    account = get_user_account(
        user=user,
        account_id=account_id,
    )

    account.delete()


def get_account_history(*, user, account_id):
    """
    Return a unified chronological history for an account.

    The history contains:
    - Expense transactions
    - Income transactions
    - Outgoing transfers
    - Incoming transfers

    Transfers remain separate database objects from transactions.
    This function only combines them for presentation.
    """

    account = get_user_account(
        user=user,
        account_id=account_id,
    )

    from apps.transactions.models import Transaction, Transfer

    transactions = (
        Transaction.objects
        .filter(
            user=user,
            account=account,
        )
        .select_related(
            "category",
            "subcategory",
            "currency",
        )
    )

    outgoing_transfers = (
        Transfer.objects
        .filter(
            user=user,
            from_account=account,
        )
        .select_related(
            "from_account",
            "to_account",
            "from_currency",
            "to_currency",
        )
    )

    incoming_transfers = (
        Transfer.objects
        .filter(
            user=user,
            to_account=account,
        )
        .select_related(
            "from_account",
            "to_account",
            "from_currency",
            "to_currency",
        )
    )

    history = []

    for transaction in transactions:

        if transaction.type == Transaction.EXPENSE:
            amount = -transaction.amount
            kind = "expense"
        else:
            amount = transaction.amount
            kind = "income"

        history.append(
            {
                "id": transaction.id,
                "kind": kind,
                "occurred_at": transaction.occurred_at,
                "category": transaction.category,
                "subcategory": transaction.subcategory,
                "description": transaction.description,
                "amount": amount,
                "currency": transaction.currency,
            }
        )

    for transfer in outgoing_transfers:

        history.append(
            {
                "id": transfer.id,
                "kind": "transfer-out",
                "occurred_at": transfer.occurred_at,
                "category": None,
                "subcategory": None,
                "description": transfer.description,
                "amount": -transfer.amount_from,
                "currency": transfer.from_currency,
                "transfer_account": transfer.to_account,
            }
        )

    for transfer in incoming_transfers:

        history.append(
            {
                "id": transfer.id,
                "kind": "transfer-in",
                "occurred_at": transfer.occurred_at,
                "category": None,
                "subcategory": None,
                "description": transfer.description,
                "amount": transfer.amount_to,
                "currency": transfer.to_currency,
                "transfer_account": transfer.from_account,
            }
        )

    history.sort(
        key=lambda item: item["occurred_at"],
        reverse=True,
    )

    return history


def reorder_accounts(*, user, account_ids):
    """
    Update the display order of all active accounts owned by the user.

    account_ids must contain exactly all active account IDs
    in the desired display order.
    """
    account_ids = list(account_ids)

    accounts = list(
        Account.objects.filter(
            user=user,
            is_active=True,
        )
    )

    if len(accounts) != len(account_ids):
        raise PermissionDenied("Invalid account list.")

    account_map = {account.id: account for account in accounts}

    if set(account_map.keys()) != set(account_ids):
        raise PermissionDenied("Invalid account list.")

    with transaction.atomic():
        for display_order, account_id in enumerate(account_ids):
            account = account_map[account_id]
            account.display_order = display_order
            account.save(update_fields=["display_order", "updated_at"])

    return get_user_accounts(user=user)