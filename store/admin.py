from django.contrib import admin

from .models import CustomerProfile, Order, OrderItem, Product, ProductReview


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = (
        "product_slug",
        "product_name",
        "size",
        "quantity",
        "unit_price",
        "line_total",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "full_name",
        "phone",
        "total",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("reference", "full_name", "email", "phone")
    readonly_fields = ("reference", "created_at", "subtotal", "shipping", "total")
    inlines = [OrderItemInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_active",)
    fieldsets = (
        ("Product details", {"fields": ("name", "slug", "category", "description", "price", "alt")}),
        ("Storefront display", {"fields": ("image", "image_path", "image_class", "size_options", "reviews", "is_active")}),
    )


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "product", "rating", "is_approved", "created_at")
    list_filter = ("is_approved", "rating", "created_at")
    search_fields = ("customer_name", "comment", "product__name")
    readonly_fields = ("created_at",)


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "profile_image")
    search_fields = ("user__username", "user__first_name", "user__last_name", "user__email", "phone")
