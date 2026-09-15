from django.db.models import Q
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models import Account
from apps.transactions.models import Transaction, Transfer


def _to_decimal(value, field_name):
    """
    Converts the received value to Decimal safely.
    """
    try:
        value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({
            field_name: "Enter a valid number."
        })

    return value


def _validate_transaction_data(
    *,
    user,
    account,
    category,
    subcategory,
    amount,
    currency,
    transaction_type,
):
    """
    Validates all business rules for an expense/income transaction.
    """

    # 1. Amount must be positive
    if amount <= 0:
        raise ValidationError({
            "amount": "Amount must be greater than zero."
        })

    # 2. Account must belong to the user
    if account.user_id != user.id:
        raise ValidationError({
            "account": "The account must belong to the transaction user."
        })

    # 3. Transaction currency must match account currency
    if account.currency_id != currency.id:
        raise ValidationError({
            "currency": (
                "The transaction currency must match "
                "the account currency."
            )
        })

    # 4. Category type must match transaction type
    if category.type != transaction_type:
        raise ValidationError({
            "category": (
                "The category type must match "
                "the transaction type."
            )
        })

    # 5. Subcategory must belong to selected category
    if subcategory.category_id != category.id:
        raise ValidationError({
            "subcategory": (
                "The subcategory must belong "
                "to the selected category."
            )
        })

    # 6. User can use default categories
    #    or their own custom categories
    if (
        not category.is_default
        and category.created_by_id != user.id
    ):
        raise ValidationError({
            "category": (
                "You can only use "
                "your own custom categories."
            )
        })

    # 7. User can use default subcategories
    #    or their own custom subcategories
    if (
        not subcategory.is_default
        and subcategory.created_by_id != user.id
    ):
        raise ValidationError({
            "subcategory": (
                "You can only use "
                "your own custom subcategories."
            )
        })


@transaction.atomic
def create_expense(
    *,
    user,
    account,
    category,
    subcategory,
    amount,
    currency,
    occurred_at,
    person=None,
    description=None,
):
    """
    Creates an expense and decreases the account balance atomically.
    """

    amount = _to_decimal(amount, "amount")

    # Lock the account.
    account = Account.objects.select_for_update().get(
        pk=account.pk,
    )

    # Validate all business rules.
    _validate_transaction_data(
        user=user,
        account=account,
        category=category,
        subcategory=subcategory,
        amount=amount,
        currency=currency,
        transaction_type=Transaction.EXPENSE,
    )

    # Create the expense.
    expense = Transaction.objects.create(
        user=user,
        account=account,
        type=Transaction.EXPENSE,
        category=category,
        subcategory=subcategory,
        amount=amount,
        currency=currency,
        occurred_at=occurred_at,
        person=person,
        description=description,
    )

    # Decrease account balance.
    account.current_balance -= amount

    account.save(
        update_fields=[
            "current_balance",
            "updated_at",
        ],
    )

    return expense


@transaction.atomic
def create_income(
    *,
    user,
    account,
    category,
    subcategory,
    amount,
    currency,
    occurred_at,
    person=None,
    description=None,
):
    """
    Creates an income and increases the account balance atomically.
    """

    amount = _to_decimal(amount, "amount")

    # Lock the account.
    account = Account.objects.select_for_update().get(
        pk=account.pk,
    )

    # Validate all business rules.
    _validate_transaction_data(
        user=user,
        account=account,
        category=category,
        subcategory=subcategory,
        amount=amount,
        currency=currency,
        transaction_type=Transaction.INCOME,
    )

    # Create the income.
    income = Transaction.objects.create(
        user=user,
        account=account,
        type=Transaction.INCOME,
        category=category,
        subcategory=subcategory,
        amount=amount,
        currency=currency,
        occurred_at=occurred_at,
        person=person,
        description=description,
    )

    # Increase account balance.
    account.current_balance += amount

    account.save(
        update_fields=[
            "current_balance",
            "updated_at",
        ],
    )

    return income


@transaction.atomic
def update_transaction(
    *,
    user,
    transaction_id,
    account,
    category,
    subcategory,
    amount,
    currency,
    occurred_at,
    person=None,
    description=None,
):
    """
    Updates an expense/income transaction and adjusts
    the account balance correctly.
    """

    amount = _to_decimal(amount, "amount")

    # Lock the transaction.
    transaction_obj = (
        Transaction.objects
        .select_for_update()
        .get(
            pk=transaction_id,
            user=user,
        )
    )

    # Lock the old account.
    old_account = (
        Account.objects
        .select_for_update()
        .get(
            pk=transaction_obj.account_id,
        )
    )

    # If the transaction stays in the same account,
    # use the SAME Python object.
    if old_account.pk == account.pk:
        new_account = old_account
    else:
        # Otherwise lock the new account separately.
        new_account = (
            Account.objects
            .select_for_update()
            .get(
                pk=account.pk,
            )
        )

    # Validate the new transaction data.
    _validate_transaction_data(
        user=user,
        account=new_account,
        category=category,
        subcategory=subcategory,
        amount=amount,
        currency=currency,
        transaction_type=transaction_obj.type,
    )

    # ---------------------------------------------------------
    # 1. Reverse the OLD transaction
    # ---------------------------------------------------------

    if transaction_obj.type == Transaction.EXPENSE:
        old_account.current_balance += transaction_obj.amount
    else:
        old_account.current_balance -= transaction_obj.amount

    # ---------------------------------------------------------
    # 2. Apply the NEW transaction
    # ---------------------------------------------------------

    if transaction_obj.type == Transaction.EXPENSE:
        new_account.current_balance -= amount
    else:
        new_account.current_balance += amount

    # ---------------------------------------------------------
    # 3. Save account balances
    # ---------------------------------------------------------

    old_account.save(
        update_fields=[
            "current_balance",
            "updated_at",
        ],
    )

    # Save the new account only if it is different.
    if new_account.pk != old_account.pk:
        new_account.save(
            update_fields=[
                "current_balance",
                "updated_at",
            ],
        )

    # ---------------------------------------------------------
    # 4. Update the transaction
    # ---------------------------------------------------------

    transaction_obj.account = new_account
    transaction_obj.category = category
    transaction_obj.subcategory = subcategory
    transaction_obj.amount = amount
    transaction_obj.currency = currency
    transaction_obj.occurred_at = occurred_at
    transaction_obj.person = person
    transaction_obj.description = description

    transaction_obj.save()

    return transaction_obj


@transaction.atomic
def delete_transaction(
    *,
    user,
    transaction_id,
):
    """
    Deletes an expense/income transaction and reverses
    its effect on the account balance.
    """

    # Lock the transaction.
    transaction_obj = (
        Transaction.objects
        .select_for_update()
        .get(
            pk=transaction_id,
            user=user,
        )
    )

    # Lock the account.
    account = (
        Account.objects
        .select_for_update()
        .get(
            pk=transaction_obj.account_id,
        )
    )

    # Reverse the transaction's effect.
    if transaction_obj.type == Transaction.EXPENSE:
        account.current_balance += transaction_obj.amount
    else:
        account.current_balance -= transaction_obj.amount

    account.save(
        update_fields=[
            "current_balance",
            "updated_at",
        ],
    )

    # Delete the transaction.
    transaction_obj.delete()


def _validate_transfer_data(
    *,
    user,
    from_account,
    to_account,
    amount_from,
    amount_to,
    from_currency,
    to_currency,
    exchange_rate,
):
    """
    Validates all business rules for a transfer.
    """

    # 1. Accounts must be different
    if from_account.id == to_account.id:
        raise ValidationError({
            "to_account": (
                "The source and destination accounts "
                "must be different."
            )
        })

    # 2. Both accounts must belong to the user
    if from_account.user_id != user.id:
        raise ValidationError({
            "from_account": (
                "The source account must belong "
                "to the transfer user."
            )
        })

    if to_account.user_id != user.id:
        raise ValidationError({
            "to_account": (
                "The destination account must belong "
                "to the transfer user."
            )
        })

    # 3. Currency must match source account
    if from_account.currency_id != from_currency.id:
        raise ValidationError({
            "from_currency": (
                "The source currency must match "
                "the source account currency."
            )
        })

    # 4. Currency must match destination account
    if to_account.currency_id != to_currency.id:
        raise ValidationError({
            "to_currency": (
                "The destination currency must match "
                "the destination account currency."
            )
        })

    # 5. Amounts must be positive
    if amount_from <= 0:
        raise ValidationError({
            "amount_from": (
                "Source amount must be greater than zero."
            )
        })

    if amount_to <= 0:
        raise ValidationError({
            "amount_to": (
                "Destination amount must be greater than zero."
            )
        })

    # 6. Exchange rate must be positive
    if exchange_rate <= 0:
        raise ValidationError({
            "exchange_rate": (
                "Exchange rate must be greater than zero."
            )
        })

    # 7. Destination amount must match exchange rate
    expected_amount_to = amount_from * exchange_rate

    if abs(expected_amount_to - amount_to) > Decimal("0.0001"):
        raise ValidationError({
            "amount_to": (
                "The destination amount does not match "
                "the source amount and exchange rate."
            )
        })


@transaction.atomic
def create_transfer(
    *,
    user,
    from_account,
    to_account,
    amount_from,
    amount_to,
    from_currency,
    to_currency,
    exchange_rate,
    occurred_at,
    description=None,
):
    """
    Creates a transfer and updates both account balances atomically.
    """

    amount_from = _to_decimal(
        amount_from,
        "amount_from",
    )

    amount_to = _to_decimal(
        amount_to,
        "amount_to",
    )

    exchange_rate = _to_decimal(
        exchange_rate,
        "exchange_rate",
    )

    # Lock both accounts.
    account_ids = sorted([
        from_account.pk,
        to_account.pk,
    ])

    locked_accounts = (
        Account.objects
        .select_for_update()
        .filter(pk__in=account_ids)
        .order_by("pk")
    )

    accounts = {
        account.pk: account
        for account in locked_accounts
    }

    # Make sure both accounts still exist.
    if from_account.pk not in accounts:
        raise ValidationError({
            "from_account": (
                "Source account does not exist."
            )
        })

    if to_account.pk not in accounts:
        raise ValidationError({
            "to_account": (
                "Destination account does not exist."
            )
        })

    from_account = accounts[from_account.pk]
    to_account = accounts[to_account.pk]

    # Validate transfer.
    _validate_transfer_data(
        user=user,
        from_account=from_account,
        to_account=to_account,
        amount_from=amount_from,
        amount_to=amount_to,
        from_currency=from_currency,
        to_currency=to_currency,
        exchange_rate=exchange_rate,
    )

    # Create transfer.
    transfer = Transfer.objects.create(
        user=user,
        from_account=from_account,
        to_account=to_account,
        amount_from=amount_from,
        amount_to=amount_to,
        from_currency=from_currency,
        to_currency=to_currency,
        exchange_rate=exchange_rate,
        occurred_at=occurred_at,
        description=description,
    )

    # Remove money from source account.
    from_account.current_balance -= amount_from

    # Add money to destination account.
    to_account.current_balance += amount_to

    from_account.save(
        update_fields=[
            "current_balance",
            "updated_at",
        ],
    )

    to_account.save(
        update_fields=[
            "current_balance",
            "updated_at",
        ],
    )

    return transfer


@transaction.atomic
def update_transfer(
    *,
    user,
    transfer_id,
    from_account,
    to_account,
    amount_from,
    amount_to,
    from_currency,
    to_currency,
    exchange_rate,
    occurred_at,
    description=None,
):
    """
    Updates a transfer and adjusts all affected account balances atomically.
    """

    amount_from = _to_decimal(
        amount_from,
        "amount_from",
    )

    amount_to = _to_decimal(
        amount_to,
        "amount_to",
    )

    exchange_rate = _to_decimal(
        exchange_rate,
        "exchange_rate",
    )

    # Lock the transfer itself.
    transfer_obj = (
        Transfer.objects
        .select_for_update()
        .get(
            pk=transfer_id,
            user=user,
        )
    )

    # We need to lock every account that can be affected:
    # old source, old destination, new source, new destination.
    account_ids = sorted({
        transfer_obj.from_account_id,
        transfer_obj.to_account_id,
        from_account.pk,
        to_account.pk,
    })

    locked_accounts = (
        Account.objects
        .select_for_update()
        .filter(pk__in=account_ids)
        .order_by("pk")
    )

    accounts = {
        account.pk: account
        for account in locked_accounts
    }

    # Make sure all new accounts exist.
    if from_account.pk not in accounts:
        raise ValidationError({
            "from_account": "Source account does not exist."
        })

    if to_account.pk not in accounts:
        raise ValidationError({
            "to_account": "Destination account does not exist."
        })

    # Use the locked database objects.
    new_from_account = accounts[from_account.pk]
    new_to_account = accounts[to_account.pk]

    # Validate the new transfer data.
    _validate_transfer_data(
        user=user,
        from_account=new_from_account,
        to_account=new_to_account,
        amount_from=amount_from,
        amount_to=amount_to,
        from_currency=from_currency,
        to_currency=to_currency,
        exchange_rate=exchange_rate,
    )

    # Old accounts.
    old_from_account = accounts[transfer_obj.from_account_id]
    old_to_account = accounts[transfer_obj.to_account_id]

    # 1. Reverse the old transfer.
    old_from_account.current_balance += transfer_obj.amount_from
    old_to_account.current_balance -= transfer_obj.amount_to

    # 2. Apply the new transfer.
    new_from_account.current_balance -= amount_from
    new_to_account.current_balance += amount_to

    # Save every affected account exactly once.
    affected_account_ids = {
        old_from_account.pk,
        old_to_account.pk,
        new_from_account.pk,
        new_to_account.pk,
    }

    for account_id in affected_account_ids:
        accounts[account_id].save(
            update_fields=[
                "current_balance",
                "updated_at",
            ],
        )

    # Update the transfer record.
    transfer_obj.from_account = new_from_account
    transfer_obj.to_account = new_to_account
    transfer_obj.amount_from = amount_from
    transfer_obj.amount_to = amount_to
    transfer_obj.from_currency = from_currency
    transfer_obj.to_currency = to_currency
    transfer_obj.exchange_rate = exchange_rate
    transfer_obj.occurred_at = occurred_at
    transfer_obj.description = description

    transfer_obj.save(
        update_fields=[
            "from_account",
            "to_account",
            "amount_from",
            "amount_to",
            "from_currency",
            "to_currency",
            "exchange_rate",
            "occurred_at",
            "description",
            "updated_at",
        ],
    )

    return transfer_obj


@transaction.atomic
def delete_transfer(
    *,
    user,
    transfer_id,
):
    """
    Deletes a transfer and reverses its effect on both account balances
    atomically.
    """

    # Lock the transfer.
    transfer_obj = (
        Transfer.objects
        .select_for_update()
        .get(
            pk=transfer_id,
            user=user,
        )
    )

    # Lock both affected accounts in a deterministic order.
    account_ids = sorted([
        transfer_obj.from_account_id,
        transfer_obj.to_account_id,
    ])

    locked_accounts = (
        Account.objects
        .select_for_update()
        .filter(pk__in=account_ids)
        .order_by("pk")
    )

    accounts = {
        account.pk: account
        for account in locked_accounts
    }

    # Make sure both accounts still exist.
    if transfer_obj.from_account_id not in accounts:
        raise ValidationError({
            "from_account": "Source account does not exist."
        })

    if transfer_obj.to_account_id not in accounts:
        raise ValidationError({
            "to_account": "Destination account does not exist."
        })

    from_account = accounts[transfer_obj.from_account_id]
    to_account = accounts[transfer_obj.to_account_id]

    # Reverse the transfer.
    from_account.current_balance += transfer_obj.amount_from
    to_account.current_balance -= transfer_obj.amount_to

    from_account.save(
        update_fields=[
            "current_balance",
            "updated_at",
        ],
    )

    to_account.save(
        update_fields=[
            "current_balance",
            "updated_at",
        ],
    )

    # Delete the transfer itself.
    transfer_obj.delete()


def get_transaction_history(
    user,
    kind=None,
    category_id=None,
    account_id=None,
    date_from=None,
    date_to=None,
    search=None,
):
    """
    Return the user's expenses, incomes and transfers
    as one chronological history.

    Optional filters:
    - kind: expense, income or transfer
    - category_id: transaction category
    - account_id: account involved in the transaction/transfer
    - date_from: inclusive start date
    - date_to: inclusive end date
    - search: searches description, person, category,
      subcategory and account names
    """

    # ---------------------------------------------------------
    # TRANSACTIONS
    # ---------------------------------------------------------

    transactions = (
        Transaction.objects
        .filter(user=user)
        .select_related(
            "account",
            "category",
            "subcategory",
            "currency",
        )
    )

    # Filter by transaction type.
    if kind == "expense":
        transactions = transactions.filter(
            type=Transaction.EXPENSE
        )

    elif kind == "income":
        transactions = transactions.filter(
            type=Transaction.INCOME
        )

    elif kind == "transfer":
        transactions = transactions.none()

    # Filter by category.
    if category_id:
        transactions = transactions.filter(
            category_id=category_id
        )

    # Filter by account.
    if account_id:
        transactions = transactions.filter(
            account_id=account_id
        )

    # Filter by date range.
    if date_from:
        transactions = transactions.filter(
            occurred_at__date__gte=date_from
        )

    if date_to:
        transactions = transactions.filter(
            occurred_at__date__lte=date_to
        )

    # Search.
    if search:
        transactions = transactions.filter(
            Q(description__icontains=search)
            | Q(person__icontains=search)
            | Q(category__name__icontains=search)
            | Q(subcategory__name__icontains=search)
            | Q(account__name__icontains=search)
        )

    history = []

    for transaction in transactions:
        amount = transaction.amount

        if transaction.type == Transaction.EXPENSE:
            amount = -amount
            transaction_kind = "expense"
        else:
            transaction_kind = "income"

        history.append(
            {
                "id": transaction.id,
                "kind": transaction_kind,
                "occurred_at": transaction.occurred_at,
                "category": transaction.category,
                "subcategory": transaction.subcategory,
                "description": transaction.description,
                "person": transaction.person,
                "amount": amount,
                "currency": transaction.currency,
                "account": transaction.account,
            }
        )

    # ---------------------------------------------------------
    # TRANSFERS
    # ---------------------------------------------------------

    transfers = (
        Transfer.objects
        .filter(user=user)
        .select_related(
            "from_account",
            "to_account",
            "from_currency",
            "to_currency",
        )
    )

    # If a specific transaction type was selected,
    # transfers should only appear for "transfer" or "all".
    if kind in {"expense", "income"}:
        transfers = transfers.none()

    # Filter by account.
    if account_id:
        transfers = transfers.filter(
            Q(from_account_id=account_id)
            | Q(to_account_id=account_id)
        )

    # Filter by date range.
    if date_from:
        transfers = transfers.filter(
            occurred_at__date__gte=date_from
        )

    if date_to:
        transfers = transfers.filter(
            occurred_at__date__lte=date_to
        )

    # Search transfers.
    if search:
        transfers = transfers.filter(
            Q(description__icontains=search)
            | Q(from_account__name__icontains=search)
            | Q(to_account__name__icontains=search)
        )

    for transfer in transfers:
        history.append(
            {
                "id": transfer.id,
                "kind": "transfer",
                "occurred_at": transfer.occurred_at,
                "description": transfer.description,
                "amount_from": transfer.amount_from,
                "amount_to": transfer.amount_to,
                "from_currency": transfer.from_currency,
                "to_currency": transfer.to_currency,
                "from_account": transfer.from_account,
                "to_account": transfer.to_account,
            }
        )

    # Newest first.
    history.sort(
        key=lambda item: item["occurred_at"],
        reverse=True,
    )

    return history