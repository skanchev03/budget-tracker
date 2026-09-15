from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.dashboard.services import (
    get_dashboard_summary,
    get_expenses_by_category,
    get_monthly_income_expenses,
    get_recent_transactions,
    get_recent_transfers,
    get_total_balance,
)


@login_required
def dashboard(request):
    summary = get_dashboard_summary(request.user)

    balance_data = get_total_balance(request.user)

    recent_transactions = get_recent_transactions(
        request.user,
        limit=10,
    )

    recent_transfers = get_recent_transfers(
        request.user,
        limit=10,
    )

    expenses_by_category = get_expenses_by_category(
        request.user,
    )

    monthly_income_expenses = get_monthly_income_expenses(
        request.user,
    )

    context = {
        "accounts": summary["accounts"],
        "account_count": summary["account_count"],
        "income": summary["income"],
        "expenses": summary["expenses"],
        "net_cash_flow": summary["net_cash_flow"],
        "transfer_count": summary["transfer_count"],

        "missing_transaction_rates": summary[
            "missing_transaction_rates"
        ],

        "total_balance": balance_data["total"],
        "base_currency": balance_data["base_currency"],
        "account_balances": balance_data["account_balances"],
        "missing_rates": balance_data["missing_rates"],

        "recent_transactions": recent_transactions,
        "recent_transfers": recent_transfers,

        "expenses_by_category": expenses_by_category,

        "monthly_income_expenses": monthly_income_expenses[
            "months"
        ],

        "monthly_missing_rates": monthly_income_expenses[
            "missing_rates"
        ],
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context,
    )