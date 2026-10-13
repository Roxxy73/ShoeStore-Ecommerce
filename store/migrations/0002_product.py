from django.core.validators import FileExtensionValidator
from django.db import migrations, models


PRODUCTS = [
    {
        "slug": "mens-leather-dress-shoes",
        "name": "Men's Leather Dress Shoes",
        "description": "Classic and stylish leather dress shoes designed for comfort and durability. Perfect for office, formal events and everyday wear.",
        "price": 45000,
        "category": "leather-shoes",
        "image_path": "store/images/shoe.png",
        "alt": "Brown leather dress shoes",
        "size_options": "39, 40, 41, 42, 43, 44, 45",
        "reviews": 120,
    },
    {
        "slug": "classic-loafers",
        "name": "Classic Loafers",
        "description": "Timeless leather loafers with a comfortable fit, easy to wear from workdays to weekends.",
        "price": 38000,
        "category": "loafers",
        "image_path": "store/images/images.jpeg",
        "alt": "Classic black leather loafers",
        "size_options": "39, 40, 41, 42, 43, 44, 45",
        "reviews": 86,
    },
    {
        "slug": "outdoor-sandals",
        "name": "Outdoor Sandals",
        "description": "Comfortable leather sandals made for everyday movement and relaxed outdoor wear.",
        "price": 22000,
        "category": "sandals-slippers",
        "image_path": "store/images/images5.jpeg",
        "alt": "Leather sandals",
        "size_options": "39, 40, 41, 42, 43, 44, 45",
        "reviews": 73,
    },
    {
        "slug": "leather-briefcase-bag",
        "name": "Leather Briefcase Bag",
        "description": "A refined leather briefcase with practical room for daily essentials and work gear.",
        "price": 55000,
        "category": "bags",
        "image_path": "store/images/background.png",
        "alt": "Brown leather briefcase bag",
        "size_options": "",
        "reviews": 18,
    },
    {
        "slug": "leather-belt",
        "name": "Leather Belt",
        "description": "A versatile leather belt with a clean finish, made to complement everyday and formal outfits.",
        "price": 8000,
        "category": "belts",
        "image_path": "",
        "image_class": "product-image-belt",
        "alt": "Brown leather belt",
        "size_options": "",
        "reviews": 27,
    },
    {
        "slug": "leather-boots",
        "name": "Leather Boots",
        "description": "Durable leather boots designed for a supportive fit and dependable everyday wear.",
        "price": 48000,
        "category": "boots",
        "image_path": "",
        "image_class": "product-image-boots",
        "alt": "Black leather boots",
        "size_options": "39, 40, 41, 42, 43, 44, 45",
        "reviews": 36,
    },
]


def add_existing_products(apps, schema_editor):
    Product = apps.get_model("store", "Product")
    for product in PRODUCTS:
        Product.objects.update_or_create(slug=product["slug"], defaults=product)


def remove_existing_products(apps, schema_editor):
    Product = apps.get_model("store", "Product")
    Product.objects.filter(slug__in=[product["slug"] for product in PRODUCTS]).delete()


class Migration(migrations.Migration):
    dependencies = [("store", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("name", models.CharField(max_length=150)),
                ("description", models.TextField()),
                ("price", models.PositiveIntegerField()),
                ("category", models.CharField(choices=[("leather-shoes", "Shoes"), ("sandals-slippers", "Sandals & Slippers"), ("loafers", "Loafers"), ("bags", "Bags"), ("belts", "Belts"), ("boots", "Boots")], max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("image", models.FileField(blank=True, upload_to="products/", validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])])),
                ("image_path", models.CharField(blank=True, help_text="Optional existing static image path, for example store/images/shoe.png.", max_length=255)),
                ("image_class", models.CharField(blank=True, max_length=80)),
                ("alt", models.CharField(blank=True, max_length=200)),
                ("size_options", models.CharField(blank=True, help_text="Comma-separated sizes, for example 39, 40, 41.", max_length=200)),
                ("reviews", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["-created_at", "name"]},
        ),
        migrations.RunPython(add_existing_products, remove_existing_products),
    ]
