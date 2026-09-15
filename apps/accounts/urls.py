from django.urls import path

from apps.accounts.views import (
    account_create,
    account_delete,
    account_detail,
    account_list,
    account_update,
    reorder_accounts_view,
)

app_name = "accounts"

urlpatterns = [
    path("", account_list, name="account_list"),
    path("create/", account_create, name="account_create"),
    path("reorder/", reorder_accounts_view, name="account_reorder"),
    path("<int:account_id>/", account_detail, name="account_detail"),
    path("<int:account_id>/edit/", account_update, name="account_update"),
    path("<int:account_id>/delete/", account_delete, name="account_delete"),
]