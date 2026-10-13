from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.http import Http404
from django.urls import reverse
from django.utils import timezone

from .forms import ProductForm
from .models import Order, OrderItem, Product, ProductReview
from .views import CATEGORIES


@staff_member_required
def admin_dashboard(request):
    if not request.user.has_perm("store.view_order"):
        raise PermissionDenied

    today = timezone.localdate()
    chart_start = today - timedelta(days=6)
    sales_by_day = {
        row["day"]: row["sales"]
        for row in (
            Order.objects.exclude(status=Order.Status.CANCELLED)
            .filter(created_at__date__gte=chart_start, created_at__date__lte=today)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(sales=Sum("total"))
        )
    }
    chart_values = [
        {
            "date": chart_start + timedelta(days=index),
            "sales": sales_by_day.get(chart_start + timedelta(days=index), 0),
        }
        for index in range(7)
    ]
    max_sales = max((point["sales"] for point in chart_values), default=0) or 1
    chart_width, chart_height, chart_padding = 600, 190, 12
    chart_points = [
        (
            chart_padding + index * (chart_width - chart_padding * 2) / 6,
            chart_height
            - chart_padding
            - (point["sales"] / max_sales) * (chart_height - chart_padding * 2),
        )
        for index, point in enumerate(chart_values)
    ]
    chart_polyline = " ".join(
        f"{x:.1f},{y:.1f}" for x, y in chart_points
    )
    chart_area = (
        f"{chart_padding},{chart_height - chart_padding} "
        f"{chart_polyline} "
        f"{chart_width - chart_padding},{chart_height - chart_padding}"
    )

    order_queryset = Order.objects.all()
    search = request.GET.get("q", "").strip()
    if search:
        order_queryset = order_queryset.filter(
            Q(full_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
            | Q(items__product_name__icontains=search)
        ).distinct()

    recent_orders = list(
        order_queryset.prefetch_related("items").order_by("-created_at")[:5]
    )
    for order in recent_orders:
        order.primary_item = order.items.first()

    order_statuses = [
        (Order.Status.PENDING, "Pending", "#d49a48"),
        (Order.Status.CONFIRMED, "Confirmed", "#e5b36a"),
        (Order.Status.DELIVERED, "Delivered", "#59b48a"),
        (Order.Status.CANCELLED, "Cancelled", "#d77d64"),
    ]
    status_values = dict(
        Order.objects.values_list("status")
        .annotate(total=Count("id"))
        .values_list("status", "total")
    )
    total_orders = Order.objects.count()
    status_counts = [
        {
            "label": label,
            "count": status_values.get(status, 0),
            "color": color,
        }
        for status, label, color in order_statuses
    ]
    donut_stops = []
    stop = 0
    for status in status_counts:
        percentage = (status["count"] / total_orders * 100) if total_orders else 0
        status["percentage"] = percentage
        donut_stops.append(
            f"{status['color']} {stop:.2f}% {stop + percentage:.2f}%"
        )
        stop += percentage
    donut_background = (
        f"conic-gradient({', '.join(donut_stops)})"
        if total_orders
        else "conic-gradient(#37312a 0% 100%)"
    )

    top_products = list(
        OrderItem.objects.values("product_slug", "product_name")
        .annotate(sold=Sum("quantity"), revenue=Sum("line_total"))
        .order_by("-sold", "product_name")[:5]
    )
    product_images = {product.slug: product.image_src for product in Product.objects.all()}
    for product in top_products:
        product["image"] = product_images.get(product["product_slug"], "")
        product["revenue_display"] = f"{product['revenue']:,}"

    latest_customers = (
        Order.objects.order_by()
        .values("email")
        .annotate(
            full_name=Max("full_name"),
            latest_order=Max("created_at"),
            order_count=Count("id"),
        )
        .order_by("-latest_order")[:5]
    )
    revenue = (
        Order.objects.exclude(status=Order.Status.CANCELLED).aggregate(
            total=Sum("total")
        )["total"]
        or 0
    )

    return render(
        request,
        "store/admin_dashboard.html",
        {
            "search": search,
            "revenue_display": f"{revenue:,}",
            "total_orders": total_orders,
            "customer_count": get_user_model().objects.filter(is_staff=False, is_superuser=False).count(),
            "product_count": Product.objects.filter(is_active=True).count(),
            "category_count": len(CATEGORIES),
            "recent_orders": recent_orders,
            "order_statuses": status_counts,
            "donut_background": donut_background,
            "top_products": top_products,
            "latest_customers": latest_customers,
            "chart_values": chart_values,
            "chart_polyline": chart_polyline,
            "chart_area": chart_area,
            "chart_max_display": f"{max_sales:,}",
            "chart_mid_display": f"{max_sales // 2:,}",
            "order_list_url": reverse("admin_orders"),
            "order_add_url": reverse("admin_orders"),
            "product_list_url": reverse("admin_products"),
            "product_add_url": reverse("admin_product_add"),
            "store_shop_url": reverse("store:shop"),
            "category_list_url": reverse("store:shop"),
            "store_url": reverse("store:home"),
            "password_change_url": reverse("admin_settings"),
            "logout_url": reverse("admin:logout"),
        },
    )


@staff_member_required
def admin_orders(request):
    if not request.user.has_perm("store.view_order"):
        raise PermissionDenied

    orders = Order.objects.prefetch_related("items")
    search = request.GET.get("q", "").strip()
    if search:
        orders = orders.filter(
            Q(full_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
            | Q(items__product_name__icontains=search)
            | Q(reference__icontains=search)
        ).distinct()

    all_orders = Order.objects.all()
    status_counts = dict(all_orders.values_list("status").annotate(total=Count("id")).values_list("status", "total"))
    counts = [
        ("Total Orders", all_orders.count(), "total"),
        ("Pending", status_counts.get(Order.Status.PENDING, 0), "pending"),
        ("Processing", status_counts.get(Order.Status.CONFIRMED, 0), "processing"),
        ("Shipped", 0, "shipped"),
        ("Delivered", status_counts.get(Order.Status.DELIVERED, 0), "delivered"),
        ("Cancelled", status_counts.get(Order.Status.CANCELLED, 0), "cancelled"),
    ]
    order_rows = list(orders.order_by("-created_at"))
    for order in order_rows:
        order.primary_item = order.items.first()
    selected = next(
        (order for order in order_rows if str(order.reference) == request.GET.get("order")),
        order_rows[0] if order_rows else None,
    )
    if selected:
        selected.admin_change_url = reverse("admin_order_detail", args=[selected.pk])
    return render(request, "store/admin_orders.html", {
        "orders": order_rows,
        "selected_order": selected,
        "order_counts": counts,
        "search": search,
        "dashboard_url": reverse("admin_dashboard"),
        "order_list_url": reverse("admin_orders"),
        "product_list_url": reverse("admin_products"),
        "category_list_url": reverse("store:shop"),
        "password_change_url": reverse("admin_settings"),
        "logout_url": reverse("admin:logout"),
        "store_url": reverse("store:home"),
    })


@staff_member_required
def admin_order_detail(request, order_id):
    order = Order.objects.prefetch_related("items").filter(pk=order_id).first()
    if order is None:
        raise Http404
    if not request.user.has_perm("store.view_order"):
        raise PermissionDenied

    if request.method == "POST":
        if not request.user.has_perm("store.change_order"):
            raise PermissionDenied
        status = request.POST.get("status")
        valid_statuses = {value for value, _label in Order.Status.choices}
        if status in valid_statuses:
            order.status = status
            order.save(update_fields=["status"])
            messages.success(request, "Order updated successfully.")
        return redirect("admin_order_detail", order_id=order.pk)

    return render(request, "store/admin_order_detail.html", {
        "order": order,
        "items": order.items.all(),
        "orders_url": reverse("admin_orders"),
        "customers_url": reverse("admin_customers"),
        "category_list_url": reverse("store:shop"),
        "dashboard_url": reverse("admin_dashboard"),
        "settings_url": reverse("admin_settings"),
        "product_list_url": reverse("admin_products"),
        "store_url": reverse("store:home"),
        "logout_url": reverse("admin:logout"),
    })


@staff_member_required
def admin_customers(request):
    if not request.user.has_perm("auth.view_user"):
        raise PermissionDenied

    User = get_user_model()
    users = User.objects.filter(is_staff=False, is_superuser=False).select_related("customer_profile").order_by("-date_joined")
    total_accounts = users.count()
    search = request.GET.get("q", "").strip()
    if search:
        users = users.filter(
            Q(username__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(customer_profile__phone__icontains=search)
        )

    order_stats = {
        entry["email"].casefold(): entry
        for entry in (
            Order.objects.exclude(email="")
            .values("email")
            .annotate(
                order_count=Count("id"),
                lifetime_value=Sum("total"),
                latest_order=Max("created_at"),
            )
        )
    }
    customers = list(users)
    for customer in customers:
        stats = order_stats.get(customer.email.casefold(), {})
        customer.order_count = stats.get("order_count", 0)
        customer.lifetime_value = stats.get("lifetime_value", 0) or 0
        customer.latest_order = stats.get("latest_order")

    return render(request, "store/admin_customers.html", {
        "customers": customers,
        "search": search,
        "total_accounts": total_accounts,
        "dashboard_url": reverse("admin_dashboard"),
        "orders_url": reverse("admin_orders"),
        "customers_url": reverse("admin_customers"),
        "category_list_url": reverse("store:shop"),
        "settings_url": reverse("admin_settings"),
        "product_list_url": reverse("admin_products"),
        "store_url": reverse("store:home"),
        "logout_url": reverse("admin:logout"),
    })


@staff_member_required
def admin_settings(request):
    if not request.user.has_perm("store.view_order"):
        raise PermissionDenied

    settings = request.session.get("store_settings", {
        "store_name": "Gaudium Opus",
        "store_email": "support@gaudiumopus.com",
        "phone": "+234 801 234 5678",
        "timezone": "(GMT+1) West Africa Time",
        "language": "English",
        "store_description": "Premium leather goods for every step of your journey. Style, comfort and durability — all in one place.",
        "store_address": "12 Freedom Street, Akure, Ondo State",
        "primary_color": "#D4AF37",
        "accent_color": "#1A1A1A",
        "order_notifications": True,
        "stock_alerts": True,
        "marketing_emails": False,
    })
    if request.method == "POST":
        if request.POST.get("settings_section") == "store-info":
            settings.update({
                "store_name": request.POST.get("store_name", "").strip()[:100],
                "store_address": request.POST.get("store_address", "").strip()[:255],
                "store_description": request.POST.get("store_description", "").strip()[:300],
                "primary_color": request.POST.get("primary_color", "#D4AF37"),
                "accent_color": request.POST.get("accent_color", "#1A1A1A"),
                "order_notifications": "order_notifications" in request.POST,
                "stock_alerts": "stock_alerts" in request.POST,
                "marketing_emails": "marketing_emails" in request.POST,
            })
            for color_key, fallback in (("primary_color", "#D4AF37"), ("accent_color", "#1A1A1A")):
                color = settings[color_key]
                if not isinstance(color, str) or len(color) != 7 or not color.startswith("#") or any(character not in "0123456789abcdefABCDEF" for character in color[1:]):
                    settings[color_key] = fallback
        else:
            settings.update({
                "store_name": request.POST.get("store_name", "").strip()[:100],
                "store_email": request.POST.get("store_email", "").strip()[:254],
                "phone": request.POST.get("phone", "").strip()[:30],
                "timezone": request.POST.get("timezone", "(GMT+1) West Africa Time"),
                "language": request.POST.get("language", "English"),
            })
            allowed_timezones = {"(GMT+1) West Africa Time", "(GMT+0) Greenwich Mean Time", "(GMT+2) Central Africa Time"}
            allowed_languages = {"English", "Français", "Español", "Português"}
            if settings["timezone"] not in allowed_timezones:
                settings["timezone"] = "(GMT+1) West Africa Time"
            if settings["language"] not in allowed_languages:
                settings["language"] = "English"
        request.session["store_settings"] = settings
        messages.success(request, "Settings saved successfully.")

    context = {
        **settings,
        "order_list_url": reverse("admin_orders"),
        "order_add_url": reverse("admin_orders"),
        "product_list_url": reverse("admin_products"),
        "product_add_url": reverse("admin_product_add"),
        "category_list_url": reverse("store:shop"),
        "store_url": reverse("store:home"),
        "password_change_url": reverse("admin_settings"),
        "logout_url": reverse("admin:logout"),
    }

    return render(request, "store/admin_settings.html", context)


def _product_admin_context(request, **extra):
    return {
        "dashboard_url": reverse("admin_dashboard"),
        "product_list_url": reverse("admin_products"),
        "product_add_url": reverse("admin_product_add"),
        "orders_url": reverse("admin_orders"),
        "customers_url": reverse("admin_customers"),
        "category_list_url": reverse("store:shop"),
        "settings_url": reverse("admin_settings"),
        "store_url": reverse("store:home"),
        "logout_url": reverse("admin:logout"),
        **extra,
    }


@staff_member_required
def admin_products(request):
    if not any(
        request.user.has_perm(permission)
        for permission in ("store.view_product", "store.add_product", "store.change_product")
    ):
        raise PermissionDenied

    products = Product.objects.all()
    search = request.GET.get("q", "").strip()
    if search:
        products = products.filter(
            Q(name__icontains=search)
            | Q(slug__icontains=search)
            | Q(description__icontains=search)
        )
    return render(
        request,
        "store/admin_products.html",
        _product_admin_context(
            request,
            products=products,
            search=search,
            total_products=Product.objects.count(),
            active_products=Product.objects.filter(is_active=True).count(),
        ),
    )


@staff_member_required
def admin_product_add(request):
    if not request.user.has_perm("store.add_product"):
        raise PermissionDenied

    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        messages.success(request, f"{product.name} was added to the storefront.")
        return redirect("admin_products")
    return render(
        request,
        "store/admin_product_form.html",
        _product_admin_context(request, form=form, is_edit=False),
    )


@staff_member_required
def admin_product_edit(request, product_id):
    if not request.user.has_perm("store.change_product"):
        raise PermissionDenied

    product = get_object_or_404(Product, pk=product_id)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        messages.success(request, f"{product.name} was updated.")
        return redirect("admin_products")
    return render(
        request,
        "store/admin_product_form.html",
        _product_admin_context(request, form=form, product=product, is_edit=True),
    )


@staff_member_required
@require_POST
def admin_product_delete(request, product_id):
    if not request.user.has_perm("store.delete_product"):
        raise PermissionDenied

    product = get_object_or_404(Product, pk=product_id)
    product_name = product.name
    product.delete()
    messages.success(request, f"{product_name} was removed from your product catalogue.")
    return redirect("admin_products")


@staff_member_required
def admin_reviews(request):
    if not any(
        request.user.has_perm(permission)
        for permission in ("store.view_productreview", "store.change_productreview", "store.delete_productreview")
    ):
        raise PermissionDenied

    reviews = ProductReview.objects.select_related("product")
    status = request.GET.get("status", "pending")
    if status == "pending":
        reviews = reviews.filter(is_approved=False)
    elif status == "approved":
        reviews = reviews.filter(is_approved=True)
    else:
        status = "all"
    search = request.GET.get("q", "").strip()
    if search:
        reviews = reviews.filter(
            Q(customer_name__icontains=search)
            | Q(comment__icontains=search)
            | Q(product__name__icontains=search)
        )
    return render(request, "store/admin_reviews.html", {
        "reviews": reviews,
        "search": search,
        "status": status,
        "pending_count": ProductReview.objects.filter(is_approved=False).count(),
        "approved_count": ProductReview.objects.filter(is_approved=True).count(),
        "dashboard_url": reverse("admin_dashboard"),
        "product_list_url": reverse("admin_products"),
        "orders_url": reverse("admin_orders"),
        "customers_url": reverse("admin_customers"),
        "category_list_url": reverse("store:shop"),
        "settings_url": reverse("admin_settings"),
        "store_url": reverse("store:home"),
        "logout_url": reverse("admin:logout"),
    })


@staff_member_required
@require_POST
def admin_review_action(request, review_id, action):
    review = get_object_or_404(ProductReview, pk=review_id)
    if action in ("approve", "reject"):
        if not request.user.has_perm("store.change_productreview"):
            raise PermissionDenied
        review.is_approved = action == "approve"
        review.save(update_fields=["is_approved"])
        messages.success(request, f"Review {('approved' if review.is_approved else 'returned to pending')}.")
    elif action == "delete":
        if not request.user.has_perm("store.delete_productreview"):
            raise PermissionDenied
        review.delete()
        messages.success(request, "Review deleted.")
    else:
        raise Http404
    return redirect("admin_reviews")
