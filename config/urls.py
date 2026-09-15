from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "",
        include("apps.users.urls"),
    ),

    path(
        "dashboard/",
        include("apps.dashboard.urls"),
    ),

    path(
        "accounts/",
        include("apps.accounts.urls"),
    ),

    path(
        "transactions/",
        include("apps.transactions.urls"),
    ),

    path(
        "categories/",
        include("apps.categories.urls"),
    ),
]

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT,
)