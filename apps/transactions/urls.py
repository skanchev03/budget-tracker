from django.urls import path

from apps.transactions.views import (
    create_transaction,
    create_transfer_view,
    delete_transaction_view,
    delete_transfer_view,
    edit_transaction,
    edit_transfer,
    subcategories_by_category,
    transaction_list,
)


urlpatterns = [
    path(
        "",
        transaction_list,
        name="transaction-list",
    ),

    path(
        "add/",
        create_transaction,
        name="transaction-create",
    ),

    path(
        "<int:transaction_id>/edit/",
        edit_transaction,
        name="transaction-edit",
    ),

    path(
        "<int:transaction_id>/delete/",
        delete_transaction_view,
        name="transaction-delete",
    ),

    path(
        "transfers/add/",
        create_transfer_view,
        name="transfer-create",
    ),

    path(
        "transfers/<int:transfer_id>/edit/",
        edit_transfer,
        name="transfer-edit",
    ),

    path(
        "transfers/<int:transfer_id>/delete/",
        delete_transfer_view,
        name="transfer-delete",
    ),

    path(
        "subcategories/",
        subcategories_by_category,
        name="subcategories-by-category",
    ),
]