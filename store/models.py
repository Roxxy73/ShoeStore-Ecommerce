import uuid

from django.conf import settings
from django.db import models
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator


PRODUCT_CATEGORY_CHOICES = [
    ("leather-shoes", "Shoes"),
    ("sandals-slippers", "Sandals & Slippers"),
    ("loafers", "Loafers"),
    ("bags", "Bags"),
    ("belts", "Belts"),
    ("boots", "Boots"),
]


class Product(models.Model):
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField()
    price = models.PositiveIntegerField()
    category = models.CharField(max_length=40, choices=PRODUCT_CATEGORY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.FileField(
        upload_to="products/",
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    image_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional existing static image path, for example store/images/shoe.png.",
    )
    image_class = models.CharField(max_length=80, blank=True)
    alt = models.CharField(max_length=200, blank=True)
    size_options = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma-separated sizes, for example 39, 40, 41.",
    )
    reviews = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at", "name"]

    def __str__(self):
        return self.name

    @property
    def sizes(self):
        return [size.strip() for size in self.size_options.split(",") if size.strip()]

    @property
    def price_display(self):
        return f"{self.price:,}"

    @property
    def image_src(self):
        if self.image:
            return self.image.url
        if self.image_path:
            if self.image_path.startswith(("http://", "https://", "/")):
                return self.image_path
            return f"{settings.STATIC_URL}{self.image_path}"
        return ""


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="customer_reviews")
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField(default="", blank=True)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(max_length=1200)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer_name} on {self.product.name} ({self.rating}/5)"


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    phone = models.CharField(max_length=30, blank=True)
    profile_image = models.FileField(
        upload_to="customer_profiles/",
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )

    def __str__(self):
        return f"Profile for {self.user.get_username()}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    delivery_notes = models.TextField(blank=True)
    subtotal = models.PositiveIntegerField()
    shipping = models.PositiveIntegerField()
    total = models.PositiveIntegerField()
    payment_method = models.CharField(max_length=50, default="Payment on delivery")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.reference}"

    @property
    def total_display(self):
        return f"{self.total:,}"

    @property
    def shipping_display(self):
        return f"{self.shipping:,}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_slug = models.SlugField(max_length=100)
    product_name = models.CharField(max_length=150)
    size = models.CharField(max_length=10, blank=True)
    quantity = models.PositiveSmallIntegerField()
    unit_price = models.PositiveIntegerField()
    line_total = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"

    @property
    def line_total_display(self):
        return f"{self.line_total:,}"
