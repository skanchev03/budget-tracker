from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.forms import CreateAccountForm, UpdateAccountForm
from apps.accounts.models import Account
from apps.accounts.services import (
    create_account,
    delete_account,
    get_account_history,
    get_user_account,
    get_user_accounts,
    reorder_accounts,
    update_account,
)
from apps.core.models import Currency


@login_required
def account_list(request):
    accounts = get_user_accounts(request.user)

    return render(
        request,
        "accounts/account_list.html",
        {
            "accounts": accounts,
        },
    )


@login_required
def account_create(request):
    if request.method == "POST":
        form = CreateAccountForm(request.POST)

        if form.is_valid():
            next_display_order = (
                Account.objects
                .filter(
                    user=request.user,
                    is_active=True,
                )
                .aggregate(
                    max_order=Max("display_order")
                )["max_order"]
            )

            if next_display_order is None:
                next_display_order = 0
            else:
                next_display_order += 1

            create_account(
                user=request.user,
                name=form.cleaned_data["name"],
                emoji=form.cleaned_data["emoji"],
                color=form.cleaned_data["color"],
                currency=form.cleaned_data["currency"],
                opening_balance=form.cleaned_data["opening_balance"],
                display_order=next_display_order,
            )

            return redirect("accounts:account_list")
    else:
        form = CreateAccountForm(
            initial={
                "currency": Currency.objects.get(code="EUR"),
            }
        )

    return render(
        request,
        "accounts/account_form.html",
        {
            "form": form,
            "title": "Create Account",
            "submit_text": "Create Account",
        },
    )


@login_required
def account_detail(request, account_id):
    account = get_user_account(
        user=request.user,
        account_id=account_id,
    )

    history = get_account_history(
        user=request.user,
        account_id=account_id,
    )

    return render(
        request,
        "accounts/account_detail.html",
        {
            "account": account,
            "history": history,
        },
    )


@login_required
def account_update(request, account_id):
    account = get_user_account(
        user=request.user,
        account_id=account_id,
    )

    if request.method == "POST":
        form = UpdateAccountForm(request.POST)

        if form.is_valid():
            update_account(
                user=request.user,
                account_id=account_id,
                name=form.cleaned_data["name"],
                emoji=form.cleaned_data["emoji"],
                color=form.cleaned_data["color"],
                display_order=form.cleaned_data["display_order"],
                is_active=form.cleaned_data["is_active"],
            )

            return redirect(
                "accounts:account_detail",
                account_id=account.id,
            )
    else:
        form = UpdateAccountForm(
            initial={
                "name": account.name,
                "emoji": account.emoji,
                "color": account.color,
                "display_order": account.display_order,
                "is_active": account.is_active,
            }
        )

    return render(
        request,
        "accounts/account_form.html",
        {
            "form": form,
            "title": "Edit Account",
            "submit_text": "Save Changes",
            "account": account,
        },
    )


@login_required
def account_delete(request, account_id):
    account = get_user_account(
        user=request.user,
        account_id=account_id,
    )

    if request.method == "POST":
        delete_account(
            user=request.user,
            account_id=account_id,
        )

        return redirect("accounts:account_list")

    return render(
        request,
        "accounts/account_confirm_delete.html",
        {
            "account": account,
        },
    )


@login_required
@require_POST
def reorder_accounts_view(request):
    try:
        data = json.loads(request.body)
        account_ids = data.get("account_ids", [])

        if not isinstance(account_ids, list):
            return JsonResponse(
                {"error": "account_ids must be a list."},
                status=400,
            )

        reorder_accounts(
            user=request.user,
            account_ids=account_ids,
        )

        return JsonResponse({"success": True})

    except (json.JSONDecodeError, TypeError):
        return JsonResponse(
            {"error": "Invalid JSON."},
            status=400,
        )

    except PermissionDenied:
        return JsonResponse(
            {"error": "You do not have permission to reorder these accounts."},
            status=403,
        )