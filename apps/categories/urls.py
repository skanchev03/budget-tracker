from django.urls import path

from apps.categories.views import (
    category_create,
    category_delete,
    category_list,
    category_update,
    subcategory_create,
    subcategory_update,
    subcategory_delete,
)


app_name = "categories"

urlpatterns = [
    path("", category_list, name="category_list"),
    path("create/", category_create, name="category_create"),
    path("<int:category_id>/edit/", category_update, name="category_update"),
    path("<int:category_id>/delete/", category_delete, name="category_delete"),
    path("subcategories/create/", subcategory_create, name="subcategory_create"),
    path("subcategories/<int:subcategory_id>/edit/", subcategory_update, name="subcategory_update"),
    path("subcategories/<int:subcategory_id>/delete/", subcategory_delete, name="subcategory_delete"),
]