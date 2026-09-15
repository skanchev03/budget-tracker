from django.db.models import Q

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.db import models

from apps.accounts.models import Account
from apps.categories.models import Category
from apps.transactions.forms import TransactionForm, TransferForm
from apps.transactions.models import Transaction, Transfer
from apps.transactions.services import (
    create_expense,
    create_income,
    create_transfer,
    delete_transaction,
    delete_transfer,
    update_transaction,
    update_transfer,
    get_transaction_history,
)


@login_required
def transaction_list(request):
    """
    Display the user's expenses, incomes and transfers
    as one chronological history with optional filters.
    """

    kind = request.GET.get("kind") or None
    category_id = request.GET.get("category") or None
    account_id = request.GET.get("account") or None
    date_from = request.GET.get("date_from") or None
    date_to = request.GET.get("date_to") or None
    search = request.GET.get("search", "").strip() or None

    history = get_transaction_history(
        user=request.user,
        kind=kind,
        category_id=category_id,
        account_id=account_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )

    # ---------------------------------------------------------
    # Filter dropdown data
    # ---------------------------------------------------------

    accounts = (
        Account.objects
        .filter(
            user=request.user,
            is_active=True,
        )
        .select_related("currency")
        .order_by("display_order", "name")
    )

    categories = (
        Category.objects
        .filter(
            Q(is_default=True)
            | Q(created_by=request.user)
        )
        .order_by("type", "name")
    )

    return render(
        request,
        "transactions/transaction_list.html",
        {
            "history": history,
            "accounts": accounts,
            "categories": categories,
        },
    )


@login_required
def create_transaction(request):
    """
    Create an Expense or Income transaction.
    """

    if request.method == "POST":
        form = TransactionForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            cleaned_data = form.cleaned_data

            transaction_type = cleaned_data["type"]

            if transaction_type == Transaction.EXPENSE:
                create_expense(
                    user=request.user,
                    account=cleaned_data["account"],
                    category=cleaned_data["category"],
                    subcategory=cleaned_data["subcategory"],
                    amount=cleaned_data["amount"],
                    currency=cleaned_data["account"].currency,
                    occurred_at=cleaned_data["occurred_at"],
                    person=cleaned_data.get("person"),
                    description=cleaned_data.get("description"),
                )

                messages.success(
                    request,
                    "Expense created successfully.",
                )

            elif transaction_type == Transaction.INCOME:
                create_income(
                    user=request.user,
                    account=cleaned_data["account"],
                    category=cleaned_data["category"],
                    subcategory=cleaned_data["subcategory"],
                    amount=cleaned_data["amount"],
                    currency=cleaned_data["account"].currency,
                    occurred_at=cleaned_data["occurred_at"],
                    person=cleaned_data.get("person"),
                    description=cleaned_data.get("description"),
                )

                messages.success(
                    request,
                    "Income created successfully.",
                )

            return redirect("transaction-list")

    else:
        form = TransactionForm(
            user=request.user,
        )

    return render(
        request,
        "transactions/transaction_form.html",
        {
            "form": form,
            "page_title": "Add transaction",
        },
    )


@login_required
def edit_transaction(request, transaction_id):
    """
    Edit an existing Expense or Income transaction.
    """

    transaction = get_object_or_404(
        Transaction,
        pk=transaction_id,
        user=request.user,
    )

    if request.method == "POST":
        form = TransactionForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            cleaned_data = form.cleaned_data

            update_transaction(
                user=request.user,
                transaction_id=transaction.id,
                account=cleaned_data["account"],
                category=cleaned_data["category"],
                subcategory=cleaned_data["subcategory"],
                amount=cleaned_data["amount"],
                currency=cleaned_data["account"].currency,
                occurred_at=cleaned_data["occurred_at"],
                person=cleaned_data.get("person"),
                description=cleaned_data.get("description"),
            )

            messages.success(
                request,
                "Transaction updated successfully.",
            )

            return redirect("transaction-list")

    else:
        form = TransactionForm(
            user=request.user,
            initial={
                "type": transaction.type,
                "account": transaction.account,
                "category": transaction.category,
                "subcategory": transaction.subcategory,
                "amount": transaction.amount,
                "occurred_at": transaction.occurred_at,
                "person": transaction.person,
                "description": transaction.description,
            },
        )

    return render(
        request,
        "transactions/transaction_form.html",
        {
            "form": form,
            "transaction": transaction,
            "page_title": "Edit transaction",
        },
    )


@login_required
def delete_transaction_view(request, transaction_id):
    """
    Delete an existing Expense or Income transaction.
    """

    transaction = get_object_or_404(
        Transaction,
        pk=transaction_id,
        user=request.user,
    )

    if request.method == "POST":
        delete_transaction(
            user=request.user,
            transaction_id=transaction.id,
        )

        messages.success(
            request,
            "Transaction deleted successfully.",
        )

        return redirect("transaction-list")

    return render(
        request,
        "transactions/transaction_confirm_delete.html",
        {
            "transaction": transaction,
        },
    )


@login_required
def create_transfer_view(request):
    """
    Create a transfer between two accounts.
    """

    if request.method == "POST":
        form = TransferForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            cleaned_data = form.cleaned_data

            create_transfer(
                user=request.user,
                from_account=cleaned_data["from_account"],
                to_account=cleaned_data["to_account"],
                amount_from=cleaned_data["amount_from"],
                amount_to=cleaned_data["amount_to"],
                from_currency=cleaned_data[
                    "from_account"
                ].currency,
                to_currency=cleaned_data[
                    "to_account"
                ].currency,
                exchange_rate=cleaned_data["exchange_rate"],
                occurred_at=cleaned_data["occurred_at"],
                description=cleaned_data.get("description"),
            )

            messages.success(
                request,
                "Transfer created successfully.",
            )

            return redirect("transaction-list")

    else:
        form = TransferForm(
            user=request.user,
        )

    return render(
        request,
        "transactions/transfer_form.html",
        {
            "form": form,
            "page_title": "Add transfer",
        },
    )


@login_required
def edit_transfer(request, transfer_id):
    """
    Edit an existing transfer.
    """

    transfer = get_object_or_404(
        Transfer,
        pk=transfer_id,
        user=request.user,
    )

    if request.method == "POST":
        form = TransferForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            cleaned_data = form.cleaned_data

            update_transfer(
                user=request.user,
                transfer_id=transfer.id,
                from_account=cleaned_data["from_account"],
                to_account=cleaned_data["to_account"],
                amount_from=cleaned_data["amount_from"],
                amount_to=cleaned_data["amount_to"],
                from_currency=cleaned_data[
                    "from_account"
                ].currency,
                to_currency=cleaned_data[
                    "to_account"
                ].currency,
                exchange_rate=cleaned_data["exchange_rate"],
                occurred_at=cleaned_data["occurred_at"],
                description=cleaned_data.get("description"),
            )

            messages.success(
                request,
                "Transfer updated successfully.",
            )

            return redirect("transaction-list")

    else:
        form = TransferForm(
            user=request.user,
            initial={
                "from_account": transfer.from_account,
                "to_account": transfer.to_account,
                "amount_from": transfer.amount_from,
                "amount_to": transfer.amount_to,
                "exchange_rate": transfer.exchange_rate,
                "occurred_at": transfer.occurred_at,
                "description": transfer.description,
            },
        )

    return render(
        request,
        "transactions/transfer_form.html",
        {
            "form": form,
            "transfer": transfer,
            "page_title": "Edit transfer",
        },
    )


@login_required
def delete_transfer_view(request, transfer_id):
    """
    Delete an existing transfer.
    """

    transfer = get_object_or_404(
        Transfer,
        pk=transfer_id,
        user=request.user,
    )

    if request.method == "POST":
        delete_transfer(
            user=request.user,
            transfer_id=transfer.id,
        )

        messages.success(
            request,
            "Transfer deleted successfully.",
        )

        return redirect("transaction-list")

    return render(
        request,
        "transactions/transfer_confirm_delete.html",
        {
            "transfer": transfer,
        },
    )


@login_required
def subcategories_by_category(request):
    """
    Return subcategories belonging to the selected category.
    """

    category_id = request.GET.get("category_id")

    if not category_id:
        return JsonResponse({"subcategories": []})

    from apps.categories.models import Subcategory

    subcategories = (
        Subcategory.objects
        .filter(
            category_id=category_id,
        )
        .filter(
            models.Q(is_default=True)
            | models.Q(created_by=request.user)
        )
        .order_by("name")
    )

    data = [
        {
            "id": subcategory.id,
            "name": subcategory.name,
        }
        for subcategory in subcategories
    ]

    return JsonResponse({"subcategories": data})