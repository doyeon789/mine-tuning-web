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

    const closeHistoryMenus = () => {
        document.querySelectorAll("[data-history-menu]").forEach((menu) => {
            menu.hidden = true;
            const renameForm = menu.querySelector("[data-history-rename-form]");
            const renameButton = menu.querySelector("[data-history-rename-button]");

            if (renameForm) {
                renameForm.hidden = true;
                const input = renameForm.querySelector("input");
                if (input) {
                    input.value = input.defaultValue;
                }
            }

            if (renameButton) {
                renameButton.hidden = false;
            }
        });
        document.querySelectorAll("[data-history-menu-button]").forEach((button) => {
            button.setAttribute("aria-expanded", "false");
        });
    };
    
    document.querySelectorAll("[data-history-menu-button]").forEach((button) => {
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

    document.querySelectorAll("[data-history-rename-button]").forEach((button) => {
        button.addEventListener("click", (event) => {
            event.stopPropagation();
            const menu = button.closest("[data-history-menu]");
            const form = menu.querySelector("[data-history-rename-form]");
            const input = form.querySelector("input");

            button.hidden = true;
            form.hidden = false;
            input.focus();
            input.select();
        });
    });

    document.querySelectorAll("[data-history-rename-cancel]").forEach((button) => {
        button.addEventListener("click", (event) => {
            event.stopPropagation();
            const form = button.closest("[data-history-rename-form]");
            const menu = form.closest("[data-history-menu]");
            const renameButton = menu.querySelector("[data-history-rename-button]");
            const input = form.querySelector("input");

            input.value = input.defaultValue;
            form.hidden = true;
            renameButton.hidden = false;
        });
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest("[data-history-item]")) {
            closeHistoryMenus();
        }
    });

    const closeAccountMenu = () => {
        const menu = document.querySelector("[data-account-menu]");
        const button = document.querySelector("[data-account-menu-button]");

        if (!menu || !button) {
            return;
        }

        menu.hidden = true;
        button.setAttribute("aria-expanded", "false");
    };

    const accountMenuButton = document.querySelector("[data-account-menu-button]");
    if (accountMenuButton) {
        accountMenuButton.addEventListener("click", (event) => {
            event.stopPropagation();
            const menu = document.querySelector("[data-account-menu]");
            const isOpen = !menu.hidden;

            closeHistoryMenus();
            menu.hidden = isOpen;
            accountMenuButton.setAttribute("aria-expanded", String(!isOpen));
        });
    }

    document.addEventListener("click", (event) => {
        if (!event.target.closest("[data-account-menu-wrap]")) {
            closeAccountMenu();
        }
    });

    document.querySelectorAll(".message-input").forEach((textarea) => {
        textarea.addEventListener("keydown", (event) => {
            if (event.key !== "Enter" || event.shiftKey || event.isComposing) {
                return;
            }

            event.preventDefault();
            const form = textarea.closest("form");
            if (form && textarea.value.trim()) {
                form.requestSubmit();
            }
        });
    });

    const messageInput = document.querySelector(".message-input");
    if (messageInput) {
        messageInput.focus();
        messageInput.setSelectionRange(messageInput.value.length, messageInput.value.length);

        document.addEventListener("keydown", (event) => {
            const target = event.target;
            const isEditableTarget =
                target instanceof HTMLInputElement ||
                target instanceof HTMLTextAreaElement ||
                target instanceof HTMLSelectElement ||
                target.isContentEditable;

            if (
                isEditableTarget ||
                event.ctrlKey ||
                event.metaKey ||
                event.altKey ||
                event.key.length !== 1
            ) {
                return;
            }

            messageInput.focus();
            messageInput.setSelectionRange(messageInput.value.length, messageInput.value.length);
        });
    }

    const resizeMessageEditInput = (textarea) => {
        textarea.style.height = "auto";
        textarea.style.height = `${textarea.scrollHeight}px`;
    };

    document.querySelectorAll("[data-edit-message]").forEach((button) => {
        button.addEventListener("click", () => {
            const form = button.closest("[data-message-form]");
            const message = form.closest(".message");
            const text = form.querySelector("[data-message-text]");
            const textarea = form.querySelector("textarea");
            const saveButton = form.querySelector(".message-edit-button");
            const cancelButton = form.querySelector(".message-cancel-button");

            message.classList.add("editing");
            text.hidden = true;
            textarea.hidden = false;
            resizeMessageEditInput(textarea);
            button.hidden = true;
            saveButton.hidden = false;
            cancelButton.hidden = false;
            textarea.focus();
            textarea.setSelectionRange(textarea.value.length, textarea.value.length);
        });
    });

    document.querySelectorAll("[data-cancel-edit]").forEach((button) => {
        button.addEventListener("click", () => {
            const form = button.closest("[data-message-form]");
            const message = form.closest(".message");
            const text = form.querySelector("[data-message-text]");
            const textarea = form.querySelector("textarea");
            const editButton = form.querySelector(".message-action-button");
            const saveButton = form.querySelector(".message-edit-button");

            message.classList.remove("editing");
            message.style.width = "";
            textarea.value = textarea.defaultValue;
            textarea.style.height = "";
            textarea.hidden = true;
            text.hidden = false;
            saveButton.hidden = true;
            button.hidden = true;
            editButton.hidden = false;
        });
    });

    document.querySelectorAll(".message-edit-input").forEach((textarea) => {
        textarea.addEventListener("input", () => resizeMessageEditInput(textarea));
    });
});
