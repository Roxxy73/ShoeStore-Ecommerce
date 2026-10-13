from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.views.generic.base import RedirectView
from django.conf.urls.static import static

from store.admin_dashboard import (
    admin_customers,
    admin_dashboard,
    admin_product_add,
    admin_product_delete,
    admin_product_edit,
    admin_products,
    admin_review_action,
    admin_reviews,
    admin_order_detail,
    admin_orders,
    admin_settings,
)

urlpatterns = [
    path("admin/dashboard/", admin_dashboard, name="admin_dashboard"),
    path("admin/products/", admin_products, name="admin_products"),
    path("admin/products/add/", admin_product_add, name="admin_product_add"),
    path("admin/products/<int:product_id>/edit/", admin_product_edit, name="admin_product_edit"),
    path("admin/products/<int:product_id>/delete/", admin_product_delete, name="admin_product_delete"),
    path("admin/reviews/", admin_reviews, name="admin_reviews"),
    path("admin/reviews/<int:review_id>/<str:action>/", admin_review_action, name="admin_review_action"),
    path("admin/orders/", admin_orders, name="admin_orders"),
    path("admin/orders/<int:order_id>/", admin_order_detail, name="admin_order_detail"),
    path("admin/customers/", admin_customers, name="admin_customers"),
    path("admin/settings/", admin_settings, name="admin_settings"),
    path(
        "admin/",
        RedirectView.as_view(pattern_name="admin_dashboard", permanent=False),
    ),
    path(
        "admin/password_reset/",
        auth_views.PasswordResetView.as_view(),
        name="admin_password_reset",
    ),
    path(
        "admin/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="admin_password_reset_done",
    ),
    path(
        "admin/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="admin_password_reset_confirm",
    ),
    path(
        "admin/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="admin_password_reset_complete",
    ),
    path("admin/", admin.site.urls),
    path("", include("store.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
