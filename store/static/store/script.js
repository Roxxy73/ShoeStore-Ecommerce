const backgroundSlides = document.querySelectorAll(".background-slide");
let activeBackgroundSlide = 0;

window.setInterval(() => {
    backgroundSlides[activeBackgroundSlide].classList.remove("is-active");
    activeBackgroundSlide = (activeBackgroundSlide + 1) % backgroundSlides.length;
    backgroundSlides[activeBackgroundSlide].classList.add("is-active");
}, 10000);

document.querySelectorAll("[data-quantity-step]").forEach((button) => {
    button.addEventListener("click", () => {
        const input = button.parentElement.querySelector('input[type="number"]');
        const step = Number(button.dataset.quantityStep);
        const min = Number(input.min) || 1;
        const max = Number(input.max) || 99;
        input.value = String(Math.min(max, Math.max(min, Number(input.value) + step)));
    });
});

const mainProductImage = document.querySelector("#main-product-image");
if (mainProductImage) {
    document.querySelectorAll(".product-thumbnail img").forEach((thumbnail) => {
        thumbnail.closest(".product-thumbnail").addEventListener("click", () => {
            mainProductImage.src = thumbnail.src;
            document.querySelectorAll(".product-thumbnail").forEach((item) => {
                item.classList.toggle("is-selected", item.contains(thumbnail));
            });
        });
    });
}
