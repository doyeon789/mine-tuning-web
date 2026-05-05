document.addEventListener("DOMContentLoaded", () => {
    const messageScroll = document.querySelector("[data-message-scroll]");
    if (messageScroll) {
        messageScroll.scrollTop = messageScroll.scrollHeight;
    }

    document.querySelectorAll("[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!window.confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });
});
