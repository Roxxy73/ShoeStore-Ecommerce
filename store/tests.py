from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from .models import Order, OrderItem, Product
from .views import CATEGORIES


class CatalogPageTests(TestCase):
    def test_homepage_category_links_open_the_matching_pages(self):
        response = self.client.get(reverse("store:home"))

        self.assertEqual(response.status_code, 200)
        for category in CATEGORIES:
            with self.subTest(category=category["slug"]):
                self.assertContains(
                    response,
                    reverse("store:category", args=[category["slug"]]),
                )

    def test_all_products_page_renders_product_catalog_and_filters(self):
        response = self.client.get(reverse("store:shop"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All Products")
        self.assertContains(response, "Filter By")
        for product in Product.objects.all():
            with self.subTest(product=product.name):
                self.assertContains(response, escape(product.name), html=False)

    def test_category_page_shows_only_the_selected_category(self):
        response = self.client.get(
            reverse("store:category", args=["loafers"])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Loafers")
        self.assertContains(response, "Classic Loafers")
        self.assertNotContains(response, "Outdoor Sandals")

    def test_shop_filters_and_sorts_products(self):
        response = self.client.get(
            reverse("store:shop"),
            {
                "category": ["leather-shoes", "loafers"],
                "price": ["20000-40000"],
                "sort": "price-low",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Classic Loafers")
        self.assertNotContains(response, "Men&#x27;s Leather Dress Shoes")

    def test_unknown_category_returns_not_found(self):
        response = self.client.get(
            reverse("store:category", args=["not-a-real-category"])
        )

        self.assertEqual(response.status_code, 404)

    def test_product_detail_has_size_and_quantity_controls(self):
        response = self.client.get(
            reverse("store:product_detail", args=["mens-leather-dress-shoes"])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Size")
        self.assertContains(response, "Quantity")
        self.assertContains(response, "Buy Now")
        self.assertContains(response, "product-gallery")

    def test_add_update_and_remove_cart_item(self):
        add_response = self.client.post(
            reverse("store:add_to_cart", args=["mens-leather-dress-shoes"]),
            {"size": "42", "quantity": "2"},
        )
        self.assertRedirects(add_response, reverse("store:cart"))

        cart_response = self.client.get(reverse("store:cart"))
        self.assertContains(cart_response, "Men&#x27;s Leather Dress Shoes")
        self.assertContains(cart_response, "₦90,000")
        self.assertContains(cart_response, "Size: 42")

        update_response = self.client.post(
            reverse("store:update_cart", args=["mens-leather-dress-shoes"]),
            {"size": "42", "quantity": "1"},
        )
        self.assertRedirects(update_response, reverse("store:cart"))
        self.assertContains(self.client.get(reverse("store:cart")), "₦45,000")

        remove_response = self.client.post(
            reverse("store:remove_from_cart", args=["mens-leather-dress-shoes"]),
            {"size": "42"},
        )
        self.assertRedirects(remove_response, reverse("store:cart"))
        self.assertContains(
            self.client.get(reverse("store:cart")),
            "Your cart is waiting for something special",
        )

    def test_add_to_cart_rejects_missing_size(self):
        response = self.client.post(
            reverse("store:add_to_cart", args=["mens-leather-dress-shoes"]),
            {"quantity": "1"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Please choose a size", status_code=400)

    def test_checkout_saves_order_and_items_then_clears_cart(self):
        self.client.post(
            reverse("store:add_to_cart", args=["mens-leather-dress-shoes"]),
            {"size": "42", "quantity": "2"},
        )

        checkout_response = self.client.post(
            reverse("store:checkout"),
            {
                "full_name": "Ada Example",
                "email": "ada@example.com",
                "phone": "+2348012345678",
                "address": "12 Example Street",
                "city": "Lagos",
                "state": "Lagos",
                "delivery_notes": "Call on arrival",
            },
        )

        order = Order.objects.get()
        self.assertRedirects(
            checkout_response,
            reverse("store:order_confirmation", args=[order.reference]),
        )
        self.assertEqual(order.subtotal, 90000)
        self.assertEqual(order.shipping, 5000)
        self.assertEqual(order.total, 95000)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.items.count(), 1)

        item = order.items.get()
        self.assertEqual(item.product_name, "Men's Leather Dress Shoes")
        self.assertEqual(item.size, "42")
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.line_total, 90000)

        confirmation = self.client.get(checkout_response.url)
        self.assertContains(confirmation, "Thank you, Ada Example.")
        self.assertContains(confirmation, "₦95,000")
        self.assertContains(confirmation, "Payment is due on delivery.")
        self.assertFalse(self.client.session.get("cart"))
        self.assertEqual(OrderItem.objects.filter(order=order).count(), 1)

    def test_checkout_requires_valid_delivery_details(self):
        self.client.post(
            reverse("store:add_to_cart", args=["leather-briefcase-bag"]),
            {"quantity": "1"},
        )

        response = self.client.post(
            reverse("store:checkout"),
            {
                "full_name": "Ada Example",
                "email": "not-an-email",
                "phone": "+2348012345678",
                "address": "12 Example Street",
                "city": "Lagos",
                "state": "Lagos",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid email address.")
        self.assertEqual(Order.objects.count(), 0)
        self.assertTrue(self.client.session.get("cart"))

    def test_checkout_redirects_when_cart_is_empty(self):
        response = self.client.get(reverse("store:checkout"))

        self.assertRedirects(response, reverse("store:cart"))


class AdminDashboardTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.admin_user = get_user_model().objects.create_superuser(
            username="dashboard-admin",
            email="admin@example.com",
            password="test-password",
        )

    def test_dashboard_requires_staff_login(self):
        response = self.client.get(reverse("admin_dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('admin:login')}?next={reverse('admin_dashboard')}",
        )

    def test_admin_index_redirects_to_dashboard(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin:index"))

        self.assertRedirects(response, reverse("admin_dashboard"))

    def test_successful_admin_login_lands_on_dashboard(self):
        password = "dashboard-test-password"
        self.admin_user.set_password(password)
        self.admin_user.save(update_fields=["password"])

        response = self.client.post(
            reverse("admin:login"),
            {
                "username": self.admin_user.username,
                "password": password,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], reverse("admin_dashboard"))

    def test_dashboard_displays_real_store_metrics_and_order_data(self):
        self.client.force_login(self.admin_user)
        order = Order.objects.create(
            full_name="Raji Andrew Oluwaseun",
            email="raji@example.com",
            phone="+2348012345678",
            address="12 Example Street",
            city="Lagos",
            state="Lagos",
            subtotal=45000,
            shipping=5000,
            total=50000,
        )
        OrderItem.objects.create(
            order=order,
            product_slug="mens-leather-dress-shoes",
            product_name="Men's Leather Dress Shoes",
            size="42",
            quantity=1,
            unit_price=45000,
            line_total=45000,
        )

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "₦50,000")
        self.assertContains(response, "Raji Andrew Oluwaseun")
        self.assertContains(response, "Men&#x27;s Leather Dress Shoes")
        self.assertContains(response, reverse("admin:store_order_changelist"))
        self.assertContains(response, "Sales Overview")

    def test_admin_can_add_a_product_that_appears_in_the_store(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("admin:store_product_add"),
            {
                "name": "New Leather Tote",
                "slug": "new-leather-tote",
                "description": "A hand-finished leather tote.",
                "price": 62000,
                "category": "bags",
                "image": "",
                "image_path": "",
                "image_class": "",
                "alt": "Leather tote bag",
                "size_options": "",
                "reviews": 0,
                "is_active": "on",
                "_save": "Save",
            },
        )

        self.assertRedirects(response, reverse("admin:store_product_changelist"))
        product = Product.objects.get(slug="new-leather-tote")
        self.assertContains(self.client.get(reverse("store:shop")), product.name)
        self.assertContains(self.client.get(reverse("store:home")), product.name)

    def test_admin_can_delete_a_product_from_the_custom_edit_page(self):
        self.client.force_login(self.admin_user)
        product = Product.objects.get(slug="classic-loafers")

        edit_response = self.client.get(reverse("admin_product_edit", args=[product.pk]))
        self.assertEqual(edit_response.status_code, 200)
        self.assertContains(edit_response, "Delete Product")

        response = self.client.post(reverse("admin_product_delete", args=[product.pk]))

        self.assertRedirects(response, reverse("admin_products"))
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
        self.assertNotContains(self.client.get(reverse("store:shop")), product.name)

    def test_dashboard_search_filters_recent_orders(self):
        self.client.force_login(self.admin_user)
        Order.objects.create(
            full_name="Raji Andrew Oluwaseun",
            email="raji@example.com",
            phone="+2348012345678",
            address="12 Example Street",
            city="Lagos",
            state="Lagos",
            subtotal=45000,
            shipping=5000,
            total=50000,
        )
        Order.objects.create(
            full_name="Ada Example",
            email="ada@example.com",
            phone="+2348098765432",
            address="4 Other Street",
            city="Abuja",
            state="FCT",
            subtotal=22000,
            shipping=5000,
            total=27000,
        )

        response = self.client.get(reverse("admin_dashboard"), {"q": "Raji"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [order.full_name for order in response.context["recent_orders"]],
            ["Raji Andrew Oluwaseun"],
        )
