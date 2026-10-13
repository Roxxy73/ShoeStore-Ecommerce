from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = "store"

urlpatterns = [
    path("account/login/", auth_views.LoginView.as_view(template_name="store/account_form.html", next_page="store:account"), name="login"),
    path("account/register/", views.register, name="register"),
    path("account/settings/", views.account_settings, name="account_settings"),
    path("account/", views.account, name="account"),
    path("account/logout/", auth_views.LogoutView.as_view(next_page="store:home"), name="logout"),
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path("shop/category/<slug:slug>/", views.category, name="category"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart, name="cart"),
    path("checkout/", views.checkout, name="checkout"),
    path(
        "order/<uuid:order_reference>/",
        views.order_confirmation,
        name="order_confirmation",
    ),
    path("cart/add/<slug:slug>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<slug:slug>/", views.update_cart, name="update_cart"),
    path("cart/remove/<slug:slug>/", views.remove_from_cart, name="remove_from_cart"),
]
