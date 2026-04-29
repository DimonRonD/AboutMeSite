document.addEventListener("DOMContentLoaded", () => {
    const cards = document.querySelectorAll(".case-card");
    cards.forEach((card, index) => {
        card.style.opacity = "0";
        card.style.transform = "translateY(10px)";

        setTimeout(() => {
            card.style.transition = "opacity 0.4s ease, transform 0.4s ease";
            card.style.opacity = "1";
            card.style.transform = "translateY(0)";
        }, 80 * index);
    });

    const heroTitle = document.querySelector("#hero-title");
    const heroDescription = document.querySelector("#hero-description");

    if (heroTitle && heroDescription) {
        const heroVariants = [
            {
                title: "Создаю digital-сервисы для бизнеса, которые дают измеримый результат",
                description:
                    "Помогаю компаниям запускать и развивать онлайн-продукты в торговле, услугах, fitness и клиентском сервисе.",
            },
            {
                title: "Запускаю для бизнеса удобные онлайн-сервисы без лишней сложности",
                description:
                    "Делаю понятные решения для клиентов и команды, чтобы вы быстрее выходили на рынок и росли в заявках.",
            },
            {
                title: "Превращаю идеи в работающие сервисы, которые приносят выручку",
                description:
                    "Главный результат: меньше рутины, быстрее запуск, выше вовлеченность и больше повторных обращений клиентов.",
            },
        ];

        let currentIndex = 0;

        const switchHeroContent = () => {
            heroTitle.classList.add("fading");
            heroDescription.classList.add("fading");

            setTimeout(() => {
                currentIndex = (currentIndex + 1) % heroVariants.length;
                heroTitle.textContent = heroVariants[currentIndex].title;
                heroDescription.textContent = heroVariants[currentIndex].description;
                heroTitle.classList.remove("fading");
                heroDescription.classList.remove("fading");
            }, 350);
        };

        setInterval(switchHeroContent, 5000);
    }
});
