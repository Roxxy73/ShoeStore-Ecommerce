from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils.text import slugify

from .models import CustomerProfile, Product, ProductReview


class ProductForm(forms.ModelForm):
    slug = forms.SlugField(
        required=False,
        help_text="Leave blank to create a web address from the product name.",
    )

    class Meta:
        model = Product
        fields = (
            "name",
            "slug",
            "category",
            "price",
            "description",
            "image",
            "image_path",
            "alt",
            "size_options",
            "is_active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "size_options": forms.TextInput(attrs={"placeholder": "39, 40, 41"}),
        }

    def clean_slug(self):
        slug = self.cleaned_data.get("slug")
        if slug:
            return slug

        base_slug = slugify(self.cleaned_data.get("name", "")) or "product"
        slug = base_slug
        suffix = 2
        existing = Product.objects.all()
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        while existing.filter(slug=slug).exists():
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug


class ProductReviewForm(forms.ModelForm):
    customer_email = forms.EmailField(label="Email used at checkout")

    class Meta:
        model = ProductReview
        fields = ("customer_name", "customer_email", "rating", "comment")
        labels = {"customer_name": "Your name", "rating": "Your rating", "comment": "Your review"}
        widgets = {
            "rating": forms.Select(choices=[("", "Choose a rating")]+[(value, f"{value} out of 5") for value in range(5, 0, -1)]),
            "comment": forms.Textarea(attrs={"rows": 4, "placeholder": "Share what you liked about this product..."}),
        }


class AccountSettingsForm(forms.ModelForm):
    email = forms.EmailField(label="Email address", widget=forms.EmailInput(attrs={"autocomplete": "email"}))

    class Meta:
        model = get_user_model()
        fields = ("first_name", "last_name", "email")
        labels = {"first_name": "First name", "last_name": "Last name"}
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        users = self._meta.model.objects.exclude(pk=self.instance.pk)
        if users.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ("phone", "profile_image")
        labels = {"phone": "Phone number", "profile_image": "Profile photo"}
        widgets = {
            "phone": forms.TelInput(attrs={"autocomplete": "tel", "placeholder": "+234 ..."}),
            "profile_image": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }

    def clean_profile_image(self):
        image = self.cleaned_data.get("profile_image")
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Choose an image smaller than 5 MB.")
        return image


class CheckoutForm(forms.Form):
    full_name = forms.CharField(
        max_length=150,
        label="Full name",
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    phone = forms.CharField(
        max_length=30,
        label="Phone number",
        widget=forms.TelInput(attrs={"autocomplete": "tel"}),
    )
    address = forms.CharField(
        max_length=255,
        label="Street address",
        widget=forms.TextInput(attrs={"autocomplete": "street-address"}),
    )
    city = forms.CharField(
        max_length=100,
        label="City",
        widget=forms.TextInput(attrs={"autocomplete": "address-level2"}),
    )
    state = forms.CharField(
        max_length=100,
        label="State",
        widget=forms.TextInput(attrs={"autocomplete": "address-level1"}),
    )
    delivery_notes = forms.CharField(
        required=False,
        label="Delivery notes (optional)",
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class BrandOwnerRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label="First name")
    last_name = forms.CharField(max_length=150, label="Last name")
    email = forms.EmailField(label="Email address")

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("first_name", "last_name", "username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if self._meta.model.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user
