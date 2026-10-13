# Gaudium Opus Leather World

## Run the Django storefront

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. Clicking **Shop Now** on a category opens its
Django category page, for example `/shop/category/leather-shoes/`. The product
catalog is at `/shop/`; selecting a product opens its detail page. Add to Cart
stores the selected size and quantity in the Django session, and `/cart/` lets
you update or remove items. Proceed to Checkout collects delivery details and
places a payment-on-delivery order. Orders are saved in the database and can be
managed at `http://127.0.0.1:8000/admin/` after creating an admin user with
`python manage.py createsuperuser`. No online payment is collected.

### Vercel host configuration

The app automatically allows Vercel's `VERCEL_URL` and
`VERCEL_PROJECT_PRODUCTION_URL` hostnames. If you use a custom domain, add it to
the Vercel project's `DJANGO_ALLOWED_HOSTS` environment variable. For multiple
domains, separate the hostnames with commas and omit `https://` and any URL path,
for example `shop.example.com,www.example.com`. Redeploy after changing the
environment variable.

To add storefront products, sign in as an admin and open
`http://127.0.0.1:8000/admin/store/product/add/`. Add the product details, upload
a JPG, PNG, or WebP image (or enter an existing static image path), set its sizes
if needed, and leave **Is active** checked to publish it. Active products appear
in the shop and the four most recently added also appear on the home page.

The standalone `index.html` remains available for static preview. Its shop,
category, product, and cart links point to the local Django server, so keep
`runserver` running while using that preview. Use **Choose Size** on a featured
shoe to open its product page, select a size, and add it to the cart. The Django
version of the storefront lives in `store/templates/store/home.html`.
