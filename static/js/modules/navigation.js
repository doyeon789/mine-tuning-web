const closeHistoryMenus = () => {
    document.querySelectorAll("[data-history-menu]").forEach((menu) => {
        menu.hidden = true;
        const item = menu.closest("[data-history-item]");
        if (!item) {
            return;
        }

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

const closeAccountMenu = () => {
    const menu = document.querySelector("[data-account-menu]");
    const button = document.querySelector("[data-account-menu-button]");

    if (!menu || !button) {
        return;
    }

    menu.hidden = true;
    button.setAttribute("aria-expanded", "false");
};

let isNavigationInitialized = false;

const toggleHistoryMenu = (button) => {
    const item = button.closest("[data-history-item]");
    const menu = item?.querySelector("[data-history-menu]");
    if (!menu) {
        return;
    }

    const shouldOpen = menu.hidden;
    closeHistoryMenus();
    closeAccountMenu();
    menu.hidden = !shouldOpen;
    button.setAttribute("aria-expanded", String(shouldOpen));
};

const startHistoryRename = (button) => {
    const item = button.closest("[data-history-item]");
    const titleTextarea = item?.querySelector("[data-history-title-textarea]");
    if (!titleTextarea) {
        return;
    }

    closeHistoryMenus();
    closeAccountMenu();
    button.hidden = true;
    titleTextarea.readOnly = false;
    titleTextarea.focus();
    titleTextarea.select();
};

const toggleAccountMenu = (button) => {
    const menu = document.querySelector("[data-account-menu]");
    if (!menu) {
        return;
    }

    const isOpen = !menu.hidden;
    closeHistoryMenus();
    menu.hidden = isOpen;
    button.setAttribute("aria-expanded", String(!isOpen));
};

const replaceSidebarContent = (appHtml) => {
    const parser = new DOMParser();
    const nextDocument = parser.parseFromString(appHtml, "text/html");
    const currentApp = document.querySelector("[data-chat-app]");
    const nextApp = nextDocument.querySelector("[data-chat-app]");
    const currentSidebar = currentApp?.querySelector(".sidebar");
    const nextSidebar = nextApp?.querySelector(".sidebar");

    if (!currentApp || !nextApp || !currentSidebar || !nextSidebar) {
        return;
    }

    currentSidebar.replaceWith(nextSidebar);
    currentApp.dataset.activeSessionId = nextApp.dataset.activeSessionId || "";

    const currentTopbar = currentApp.querySelector(".chat-topbar");
    const nextTopbar = nextApp.querySelector(".chat-topbar");
    if (currentTopbar && nextTopbar) {
        currentTopbar.replaceWith(nextTopbar);
    }
};

const submitHistoryForm = async (form) => {
    const activeSessionId =
        document.querySelector("[data-chat-app]")?.dataset.activeSessionId;
    const response = await fetch(form.action, {
        method: form.method || "POST",
        body: new FormData(form),
        headers: {
            "X-Requested-With": "XMLHttpRequest",
            ...(activeSessionId ? { "X-Active-Session": activeSessionId } : {}),
        },
    });

    if (!response.ok) {
        window.location.href = form.action;
        return;
    }

    const data = await response.json();
    if (data.redirect_url) {
        window.location.href = data.redirect_url;
        return;
    }

    if (data.app_html) {
        replaceSidebarContent(data.app_html);
    }
};

export const initializeNavigation = () => {
    if (isNavigationInitialized) {
        return;
    }

    document.addEventListener("click", (event) => {
        if (!(event.target instanceof Element)) {
            return;
        }

        const historyMenuButton = event.target.closest(
            "[data-history-menu-button]",
        );
        if (historyMenuButton) {
            event.stopPropagation();
            toggleHistoryMenu(historyMenuButton);
            return;
        }

        const historyRenameButton = event.target.closest(
            "[data-history-rename-button]",
        );
        if (historyRenameButton) {
            event.stopPropagation();
            startHistoryRename(historyRenameButton);
            return;
        }

        const titleTextarea = event.target.closest(
            "[data-history-title-textarea]",
        );
        if (titleTextarea?.readOnly) {
            const form = titleTextarea.closest("[data-history-title-form]");
            if (form?.dataset.sessionUrl) {
                window.location.href = form.dataset.sessionUrl;
                return;
            }
        }

        const accountMenuButton = event.target.closest(
            "[data-account-menu-button]",
        );
        if (accountMenuButton) {
            event.stopPropagation();
            toggleAccountMenu(accountMenuButton);
            return;
        }

        if (!event.target.closest("[data-history-item]")) {
            closeHistoryMenus();
        }
        if (!event.target.closest("[data-account-menu-wrap]")) {
            closeAccountMenu();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (!(event.target instanceof Element)) {
            return;
        }

        const titleTextarea = event.target.closest(
            "[data-history-title-textarea]",
        );
        if (!titleTextarea) {
            return;
        }

        if (event.key === "Escape") {
            event.preventDefault();
            titleTextarea.value = titleTextarea.defaultValue;
            closeHistoryMenus();
            return;
        }

        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            titleTextarea.closest("[data-history-title-form]")?.requestSubmit();
        }
    });

    document.addEventListener("submit", (event) => {
        const form = event.target;
        if (
            !(form instanceof HTMLFormElement) ||
            !form.matches("[data-history-ajax-form]")
        ) {
            return;
        }

        const confirmationMessage =
            event.submitter?.dataset.confirm || form.dataset.confirm;
        if (confirmationMessage && !window.confirm(confirmationMessage)) {
            event.preventDefault();
            return;
        }

        event.preventDefault();
        void submitHistoryForm(form);
    });

    isNavigationInitialized = true;
};
