export const initializeConfirmations = () => {
    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const confirmationMessage =
                event.submitter?.dataset.confirm || form.dataset.confirm;
            if (
                confirmationMessage &&
                !window.confirm(confirmationMessage)
            ) {
                event.preventDefault();
            }
        });
    });
};
