const closeHistoryMenus = () => {
    document.querySelectorAll("[data-history-menu]").forEach((menu) => {
        menu.hidden = true;
        const item = menu.closest("[data-history-item]");
        const titleTextarea = item.querySelector(
            "[data-history-title-textarea]",
        );
        const renameButton = menu.querySelector(
            "[data-history-rename-button]",
        );

        if (titleTextarea) {
            titleTextarea.readOnly = true;
            titleTextarea.value = titleTextarea.defaultValue;
        }

        if (renameButton) {
            renameButton.hidden = false;
        }
    });

    document
        .querySelectorAll("[data-history-menu-button]")
        .forEach((button) => {
            button.setAttribute("aria-expanded", "false");
        });
};

const initializeHistoryMenus = () => {
    document
        .querySelectorAll("[data-history-menu-button]")
        .forEach((button) => {
            button.addEventListener("click", (event) => {
                event.stopPropagation();
                const item = button.closest("[data-history-item]");
                const menu = item.querySelector("[data-history-menu]");
                const shouldOpen = menu.hidden;

                closeHistoryMenus();
                menu.hidden = !shouldOpen;
                button.setAttribute("aria-expanded", String(shouldOpen));
            });
        });

    document
        .querySelectorAll("[data-history-rename-button]")
        .forEach((button) => {
            button.addEventListener("click", (event) => {
                event.stopPropagation();
                const item = button.closest("[data-history-item]");
                const titleTextarea = item.querySelector(
                    "[data-history-title-textarea]",
                );

                closeHistoryMenus();
                button.hidden = true;
                titleTextarea.readOnly = false;
                titleTextarea.focus();
                titleTextarea.select();
            });
        });

    document
        .querySelectorAll("[data-history-title-form]")
        .forEach((form) => {
            const titleTextarea = form.querySelector(
                "[data-history-title-textarea]",
            );

            titleTextarea.addEventListener("click", () => {
                if (titleTextarea.readOnly) {
                    window.location.href = form.dataset.sessionUrl;
                }
            });

            titleTextarea.addEventListener("keydown", (event) => {
                if (event.key === "Escape") {
                    event.preventDefault();
                    titleTextarea.value = titleTextarea.defaultValue;
                    closeHistoryMenus();
                    return;
                }

                if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    form.requestSubmit();
                }
            });
        });
};

const closeAccountMenu = () => {
    const menu = document.querySelector("[data-account-menu]");
    const button = document.querySelector("[data-account-menu-button]");

    if (!menu || !button) {
        return;
    }

    menu.hidden = true;
    button.setAttribute("aria-expanded", "false");
};

const initializeAccountMenu = () => {
    const accountMenuButton = document.querySelector(
        "[data-account-menu-button]",
    );
    if (!accountMenuButton) {
        return;
    }

    accountMenuButton.addEventListener("click", (event) => {
        event.stopPropagation();
        const menu = document.querySelector("[data-account-menu]");
        const isOpen = !menu.hidden;

        closeHistoryMenus();
        menu.hidden = isOpen;
        accountMenuButton.setAttribute("aria-expanded", String(!isOpen));
    });
};

export const initializeNavigation = () => {
    initializeHistoryMenus();
    initializeAccountMenu();

    document.addEventListener("click", (event) => {
        if (!event.target.closest("[data-history-item]")) {
            closeHistoryMenus();
        }
        if (!event.target.closest("[data-account-menu-wrap]")) {
            closeAccountMenu();
        }
    });
};
