from django.contrib import messages
from django.db import transaction
from django.db.models import Avg, Count
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import AccountSettingsForm, BrandOwnerRegistrationForm, CheckoutForm, CustomerProfileForm, ProductReviewForm
from .models import CustomerProfile, Order, OrderItem, Product, ProductReview, PRODUCT_CATEGORY_CHOICES

CATEGORIES = [
    {"slug": slug, "name": name}
    for slug, name in PRODUCT_CATEGORY_CHOICES
]

PRICE_RANGES = [
    {"value": "0-20000", "label": "₦0 – ₦20,000", "minimum": 0, "maximum": 20000},
    {
        "value": "20000-40000",
        "label": "₦20,000 – ₦40,000",
        "minimum": 20000,
        "maximum": 40000,
    },
    {
        "value": "40000-60000",
        "label": "₦40,000 – ₦60,000",
        "minimum": 40000,
        "maximum": 60000,
    },
    {"value": "60000-plus", "label": "₦60,000+", "minimum": 60000, "maximum": None},
]

SORT_OPTIONS = [
    {"value": "newest", "label": "Newest"},
    {"value": "price-low", "label": "Price: Low to High"},
    {"value": "price-high", "label": "Price: High to Low"},
]


def _shop_context(request, path_category=None):
    valid_categories = {category["slug"] for category in CATEGORIES}
    selected_categories = set(request.GET.getlist("category")) & valid_categories
    if path_category:
        selected_categories = {path_category}

    selected_prices = {
        value
        for value in request.GET.getlist("price")
        if value in {price["value"] for price in PRICE_RANGES}
    }


    products = list(Product.objects.filter(is_active=True))
    sizes = sorted({size for product in products for size in product.sizes})
    selected_sizes = set(request.GET.getlist("size")) & set(sizes)
    sort = request.GET.get("sort", "newest")
    if sort not in {option["value"] for option in SORT_OPTIONS}:
        sort = "newest"

    if selected_categories:
        products = [product for product in products if product.category in selected_categories]

    if selected_prices:
        ranges = [item for item in PRICE_RANGES if item["value"] in selected_prices]
        products = [
            product
            for product in products
            if any(
                product.price >= price_range["minimum"]
                and (
                    price_range["maximum"] is None
                    or product.price <= price_range["maximum"]
                )
                for price_range in ranges
            )
        ]

    if selected_sizes:
        products = [
            product
            for product in products
            if selected_sizes.intersection(product.sizes)
        ]

    if sort == "price-low":
        products.sort(key=lambda product: product.price)
    elif sort == "price-high":
        products.sort(key=lambda product: product.price, reverse=True)

    display_slug = path_category
    if not display_slug and len(selected_categories) == 1:
        display_slug = next(iter(selected_categories))
    display_category = next(
        (
            category["name"]
            for category in CATEGORIES
            if category["slug"] == display_slug
        ),
        None,
    )

    return {
        "products": products,
        "categories": CATEGORIES,
        "price_ranges": PRICE_RANGES,
        "sizes": sizes,
        "sort_options": SORT_OPTIONS,
        "selected_categories": selected_categories,
        "selected_prices": selected_prices,
        "selected_sizes": selected_sizes,
        "sort": sort,
        "display_category": display_category,
        "product_count": len(products),
        "cart_count": _cart_items(request)[2],
    }


def register(request):
    if request.user.is_authenticated:
        return redirect("store:account")
    form = BrandOwnerRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("store:account")
    return render(request, "store/account_form.html", {
        "form": form,
        "form_title": "Create your account",
        "form_intro": "Join Gaudium Opus to create your brand owner account.",
        "submit_label": "Create Account",
        "is_registration": True,
    })


@login_required
def account(request):
    return render(request, "store/account.html", {
        "account_orders": Order.objects.filter(email__iexact=request.user.email).order_by("-created_at")[:10],
    })


@login_required
def account_settings(request):
    form = AccountSettingsForm(request.POST or None, instance=request.user)
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    profile_form = CustomerProfileForm(
        request.POST or None,
        request.FILES or None,
        instance=profile,
    )
    if request.method == "POST" and form.is_valid() and profile_form.is_valid():
        form.save()
        profile_form.save()
        messages.success(request, "Your account settings have been saved.")
        next_url = request.POST.get("next", "")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("store:account_settings")
    return render(request, "store/account_settings.html", {"form": form, "profile_form": profile_form})


def home(request):
    return render(
        request,
        "store/home.html",
        {
            "cart_count": _cart_items(request)[2],
            "featured_products": Product.objects.filter(is_active=True).order_by("-created_at"),
        },
    )


def shop(request):
    return render(request, "store/category.html", _shop_context(request))


def category(request, slug):
    valid_categories = {category["slug"] for category in CATEGORIES}
    if slug not in valid_categories:
        raise Http404("This product category does not exist.")

    return render(
        request,
        "store/category.html",
        _shop_context(request, path_category=slug),
    )


def _get_product(slug):
    return get_object_or_404(Product, slug=slug, is_active=True)


def _cart_items(request):
    cart_data = request.session.get("cart", {})
    items = []
    total = 0
    quantity_total = 0

    product_map = {product.slug: product for product in Product.objects.filter(is_active=True)}
    for key, entry in cart_data.items():
        product = product_map.get(entry.get("slug"))
        if product is None:
            continue
        quantity = max(1, int(entry.get("quantity", 1)))
        size = entry.get("size", "")
        line_total = product.price * quantity
        items.append(
            {
                "product": product,
                "quantity": quantity,
                "size": size,
                "line_total": line_total,
                "line_total_display": f"{line_total:,}",
                "key": key,
            }
        )
        total += line_total
        quantity_total += quantity

    return items, total, quantity_total


def product_detail(request, slug):
    product = _get_product(slug)
    _, _, cart_count = _cart_items(request)
    review_form = ProductReviewForm(request.POST or None)
    if request.method == "POST":
        if review_form.is_valid():
            has_received_product = Order.objects.filter(
                email__iexact=review_form.cleaned_data["customer_email"],
                status=Order.Status.DELIVERED,
                items__product_slug=product.slug,
            ).exists()
            if not has_received_product:
                review_form.add_error(
                    "customer_email",
                    "We could not find a delivered order for this product with that email.",
                )
            else:
                review = review_form.save(commit=False)
                review.product = product
                review.save()
                messages.success(request, "Thanks for your review. It will appear after our team approves it.")
                return redirect(f"{reverse('store:product_detail', args=[product.slug])}#customer-reviews")

    reviews = product.customer_reviews.filter(is_approved=True)
    review_summary = reviews.aggregate(count=Count("id"), average=Avg("rating"))
    return render(
        request,
        "store/product_detail.html",
        {
            "product": product,
            "cart_count": cart_count,
            "review_form": review_form,
            "customer_reviews": reviews,
            "review_count": review_summary["count"],
            "average_rating": review_summary["average"] or 0,
        },
    )


def cart(request):
    items, subtotal, cart_count = _cart_items(request)
    shipping = 0 if not items or subtotal >= 100000 else 5000
    return render(
        request,
        "store/cart.html",
        {
            "items": items,
            "subtotal": subtotal,
            "subtotal_display": f"{subtotal:,}",
            "cart_count": cart_count,
            "shipping": shipping,
            "shipping_display": f"{shipping:,}",
            "total_display": f"{subtotal + shipping:,}",
            "free_shipping_remaining": max(0, 100000 - subtotal),
            "free_shipping_remaining_display": f"{max(0, 100000 - subtotal):,}",
        },
    )


def checkout(request):
    items, subtotal, cart_count = _cart_items(request)
    if not items:
        return redirect("store:cart")

    shipping = 0 if subtotal >= 100000 else 5000
    form = CheckoutForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            order = Order.objects.create(
                **form.cleaned_data,
                subtotal=subtotal,
                shipping=shipping,
                total=subtotal + shipping,
            )
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product_slug=item["product"].slug,
                        product_name=item["product"].name,
                        size=item["size"],
                        quantity=item["quantity"],
                        unit_price=item["product"].price,
                        line_total=item["line_total"],
                    )
                    for item in items
                ]
            )
            request.session["cart"] = {}

        return redirect(
            "store:order_confirmation",
            order_reference=order.reference,
        )

    return render(
        request,
        "store/checkout.html",
        {
            "form": form,
            "items": items,
            "subtotal": subtotal,
            "subtotal_display": f"{subtotal:,}",
            "shipping": shipping,
            "shipping_display": f"{shipping:,}",
            "total_display": f"{subtotal + shipping:,}",
            "cart_count": cart_count,
        },
    )


def order_confirmation(request, order_reference):
    order = get_object_or_404(Order, reference=order_reference)
    return render(request, "store/order_confirmation.html", {"order": order})


@require_POST
def add_to_cart(request, slug):
    product = _get_product(slug)
    quantity_raw = request.POST.get("quantity", "1")
    try:
        quantity = int(quantity_raw)
    except ValueError:
        quantity = 0
    if quantity < 1 or quantity > 99:
        return render(
            request,
            "store/product_detail.html",
            {
                "product": product,
                "cart_count": _cart_items(request)[2],
                "error": "Choose a quantity between 1 and 99.",
            },
            status=400,
        )

    size = request.POST.get("size", "").strip()
    if product.sizes and size not in product.sizes:
        return render(
            request,
            "store/product_detail.html",
            {
                "product": product,
                "cart_count": _cart_items(request)[2],
                "error": "Please choose a size before adding this item to your cart.",
            },
            status=400,
        )
    if not product.sizes:
        size = ""

    cart_data = request.session.get("cart", {})
    key = f"{slug}:{size}"
    existing = cart_data.get(key, {})
    cart_data[key] = {
        "slug": slug,
        "size": size,
        "quantity": min(99, max(0, int(existing.get("quantity", 0))) + quantity),
    }
    request.session["cart"] = cart_data
    return redirect("store:cart")


@require_POST
def update_cart(request, slug):
    product = _get_product(slug)
    size = request.POST.get("size", "").strip()
    if product.sizes and size not in product.sizes:
        return redirect("store:cart")

    key = f"{slug}:{size}"
    cart_data = request.session.get("cart", {})
    if key not in cart_data:
        return redirect("store:cart")

    try:
        quantity = int(request.POST.get("quantity", "1"))
    except ValueError:
        quantity = 0

    if quantity <= 0:
        cart_data.pop(key)
    else:
        cart_data[key]["quantity"] = min(quantity, 99)
    request.session["cart"] = cart_data
    return redirect("store:cart")


@require_POST
def remove_from_cart(request, slug):
    product = _get_product(slug)
    size = request.POST.get("size", "").strip()
    if product.sizes and size not in product.sizes:
        return redirect("store:cart")

    cart_data = request.session.get("cart", {})
    cart_data.pop(f"{slug}:{size}", None)
    request.session["cart"] = cart_data
    return redirect("store:cart")
