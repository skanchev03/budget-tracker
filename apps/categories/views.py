from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.categories.forms import CategoryForm, SubcategoryForm
from apps.categories.services import (
    create_category,
    create_subcategory,
    delete_category,
    delete_subcategory,
    get_categories_for_user,
    get_category_for_user,
    get_subcategories_for_user,
    get_subcategory_for_user,
    update_category,
    update_subcategory,
)


@login_required
def category_list(request):
    categories = get_categories_for_user(request.user)
    subcategories = get_subcategories_for_user(request.user)

    return render(
        request,
        "categories/category_list.html",
        {
            "categories": categories,
            "subcategories": subcategories,
        },
    )


@login_required
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST, user=request.user)

        if form.is_valid():
            create_category(
                request.user,
                name=form.cleaned_data["name"],
                emoji=form.cleaned_data["emoji"],
                category_type=form.cleaned_data["type"],
            )

            return redirect("categories:category_list")
    else:
        form = CategoryForm(user=request.user)

    return render(
        request,
        "categories/category_form.html",
        {
            "form": form,
            "title": "Create Category",
        },
    )


@login_required
def category_update(request, category_id):
    category = get_category_for_user(
        request.user,
        category_id,
    )

    if request.method == "POST":
        form = CategoryForm(
            request.POST,
            user=request.user,
            instance=category,
        )

        if form.is_valid():
            update_category(
                request.user,
                category,
                name=form.cleaned_data["name"],
                emoji=form.cleaned_data["emoji"],
                category_type=form.cleaned_data["type"],
            )

            return redirect("categories:category_list")
    else:
        form = CategoryForm(
            user=request.user,
            instance=category,
        )

    return render(
        request,
        "categories/category_form.html",
        {
            "form": form,
            "title": "Edit Category",
            "category": category,
        },
    )


@login_required
def category_delete(request, category_id):
    category = get_category_for_user(
        request.user,
        category_id,
    )

    if request.method == "POST":
        delete_category(
            request.user,
            category,
        )

        return redirect("categories:category_list")

    return render(
        request,
        "categories/category_confirm_delete.html",
        {
            "category": category,
        },
    )


@login_required
def subcategory_create(request):
    if request.method == "POST":
        form = SubcategoryForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            create_subcategory(
                request.user,
                category=form.cleaned_data["category"],
                name=form.cleaned_data["name"],
            )

            return redirect("categories:category_list")
    else:
        form = SubcategoryForm(user=request.user)

    return render(
        request,
        "categories/subcategory_form.html",
        {
            "form": form,
            "title": "Create Subcategory",
        },
    )


@login_required
def subcategory_update(request, subcategory_id):
    subcategory = get_subcategory_for_user(
        request.user,
        subcategory_id,
    )

    if request.method == "POST":
        form = SubcategoryForm(
            request.POST,
            user=request.user,
            instance=subcategory,
        )

        if form.is_valid():
            update_subcategory(
                request.user,
                subcategory,
                category=form.cleaned_data["category"],
                name=form.cleaned_data["name"],
            )

            return redirect("categories:category_list")
    else:
        form = SubcategoryForm(
            user=request.user,
            instance=subcategory,
        )

    return render(
        request,
        "categories/subcategory_form.html",
        {
            "form": form,
            "title": "Edit Subcategory",
            "subcategory": subcategory,
        },
    )


@login_required
def subcategory_delete(request, subcategory_id):
    subcategory = get_subcategory_for_user(
        request.user,
        subcategory_id,
    )

    if request.method == "POST":
        delete_subcategory(
            request.user,
            subcategory,
        )

        return redirect("categories:category_list")

    return render(
        request,
        "categories/subcategory_confirm_delete.html",
        {
            "subcategory": subcategory,
        },
    )