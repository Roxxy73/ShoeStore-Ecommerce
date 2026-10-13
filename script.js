const backgroundSlides = document.querySelectorAll(".background-slide");
let activeBackgroundSlide = 0;

window.setInterval(() => {
    backgroundSlides[activeBackgroundSlide].classList.remove("is-active");
    activeBackgroundSlide = (activeBackgroundSlide + 1) % backgroundSlides.length;
    backgroundSlides[activeBackgroundSlide].classList.add("is-active");
}, 10000);
