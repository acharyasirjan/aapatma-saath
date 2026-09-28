document.addEventListener("DOMContentLoaded", function () {

    console.log("Aapatma Saath loaded successfully.");

    const links = document.querySelectorAll(
        'a[href^="#"]'
    );

    links.forEach(function (link) {

        link.addEventListener("click", function (event) {

            const targetId =
                this.getAttribute("href");

            if (
                targetId &&
                targetId !== "#"
            ) {

                const target =
                    document.querySelector(targetId);

                if (target) {

                    event.preventDefault();

                    target.scrollIntoView({
                        behavior: "smooth"
                    });

                }

            }

        });

    });

});