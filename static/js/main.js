document.addEventListener("DOMContentLoaded", () => {
    const pendingDraftStorageKey = "mine-chat-pending-draft";
    let isChatResponsePending = false;
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
            const item = menu.closest("[data-history-item]");
            const titleTextarea = item.querySelector("[data-history-title-textarea]");
            const renameButton = menu.querySelector("[data-history-rename-button]");

            if (titleTextarea) {
                titleTextarea.readOnly = true;
                titleTextarea.value = titleTextarea.defaultValue;
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
            const item = button.closest("[data-history-item]");
            const titleTextarea = item.querySelector("[data-history-title-textarea]");

            closeHistoryMenus();
            button.hidden = true;
            titleTextarea.readOnly = false;
            titleTextarea.focus();
            titleTextarea.select();
        });
    });

    document.querySelectorAll("[data-history-title-form]").forEach((form) => {
        const titleTextarea = form.querySelector("[data-history-title-textarea]");

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

        textarea.addEventListener("input", () => {
            if (textarea.dataset.preserveDraft !== "true") {
                return;
            }

            if (textarea.value) {
                sessionStorage.setItem(pendingDraftStorageKey, textarea.value);
            } else {
                sessionStorage.removeItem(pendingDraftStorageKey);
            }
        });
    });

    const showPendingResponse = (content, showUserMessage) => {
        const host = document.querySelector("[data-pending-response-host]");
        if (!host || host.querySelector("[data-pending-response]")) {
            return;
        }

        const emptyState = host.querySelector(".empty-state");
        if (emptyState) {
            emptyState.remove();
        }

        if (showUserMessage) {
            const pendingUserMessage = document.createElement("article");
            const pendingUserContent = document.createElement("div");

            pendingUserMessage.className = "message user pending-user-message";
            pendingUserMessage.dataset.pendingUserMessage = "";
            pendingUserContent.className = "message-content";
            pendingUserContent.textContent = content;
            pendingUserMessage.appendChild(pendingUserContent);
            host.appendChild(pendingUserMessage);
        }

        const pendingResponse = document.createElement("article");
        pendingResponse.className = "message assistant pending-response";
        pendingResponse.dataset.pendingResponse = "";
        pendingResponse.setAttribute("role", "status");
        pendingResponse.setAttribute("aria-live", "polite");
        pendingResponse.innerHTML = `
            <div class="message-content pending-response-content">
                <span>답변 생성 중</span>
                <span class="pending-response-dots" aria-hidden="true">
                    <span></span><span></span><span></span>
                </span>
            </div>
        `;

        host.hidden = false;
        host.appendChild(pendingResponse);

        const messageScroll = document.querySelector("[data-message-scroll]");
        if (messageScroll) {
            messageScroll.scrollTop = messageScroll.scrollHeight;
        }
    };

    const removeMessagesAfter = (form) => {
        if (!form.matches("[data-message-form]")) {
            return;
        }

        const editedMessage = form.closest(".message");
        let nextMessage = editedMessage?.nextElementSibling;

        while (nextMessage) {
            const messageToRemove = nextMessage;
            nextMessage = nextMessage.nextElementSibling;
            messageToRemove.remove();
        }
    };

    const finishMessageEdit = (form, submittedContent) => {
        if (!form.matches("[data-message-form]")) {
            return;
        }

        const message = form.closest(".message");
        const text = form.querySelector("[data-message-text]");
        const textarea = form.querySelector("textarea");
        const editButton = form.querySelector("[data-edit-message]");
        const saveButton = form.querySelector(".message-edit-button");
        const cancelButton = form.querySelector("[data-cancel-edit]");

        message.classList.remove("editing");
        message.style.width = "";
        text.textContent = submittedContent;
        text.hidden = false;
        textarea.hidden = true;
        saveButton.hidden = true;
        cancelButton.hidden = true;
        editButton.hidden = false;
        editButton.disabled = true;
    };

    document.querySelectorAll("[data-chat-submit-form]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (isChatResponsePending || form.dataset.submitting === "true") {
                event.preventDefault();
                return;
            }

            const contentInput = form.querySelector("[name='content']");
            if (!contentInput || !contentInput.value.trim()) {
                event.preventDefault();
                return;
            }

            const submittedContent = contentInput.value.trim();

            isChatResponsePending = true;
            form.dataset.submitting = "true";
            form.setAttribute("aria-busy", "true");

            document.querySelectorAll("[data-chat-submit-form]").forEach((chatForm) => {
                chatForm.querySelectorAll("button[type='submit']").forEach((button) => {
                    button.disabled = true;
                });
            });

            if (contentInput.classList.contains("message-input")) {
                const submittedContentInput = document.createElement("input");
                submittedContentInput.type = "hidden";
                submittedContentInput.name = "content";
                submittedContentInput.value = contentInput.value;
                form.appendChild(submittedContentInput);

                contentInput.removeAttribute("name");
                contentInput.required = false;
                contentInput.value = "";
                contentInput.dataset.preserveDraft = "true";
                sessionStorage.removeItem(pendingDraftStorageKey);
            } else if (contentInput instanceof HTMLTextAreaElement) {
                contentInput.readOnly = true;

                const messageComposerInput = document.querySelector(".message-input");
                if (messageComposerInput) {
                    messageComposerInput.dataset.preserveDraft = "true";
                    if (messageComposerInput.value) {
                        sessionStorage.setItem(
                            pendingDraftStorageKey,
                            messageComposerInput.value
                        );
                    }
                }
            }

            finishMessageEdit(form, submittedContent);
            removeMessagesAfter(form);

            const firstChat = document.querySelector("[data-first-chat]");
            if (firstChat) {
                firstChat.classList.add("is-submitting");
                document.querySelector("[data-first-chat-heading]")?.setAttribute("hidden", "");
                document.querySelector("[data-example-questions]")?.setAttribute("hidden", "");
            }

            const submitButton = form.querySelector("button[type='submit']");
            if (submitButton?.classList.contains("send-button")) {
                submitButton.classList.add("is-loading");
                submitButton.setAttribute("aria-label", "답변 생성 중");
            } else if (submitButton) {
                submitButton.classList.add("is-loading");
                submitButton.textContent = "생성 중...";
                submitButton.setAttribute("aria-label", "답변 생성 중");
            }

            showPendingResponse(
                submittedContent,
                !form.matches("[data-message-form]")
            );
        });
    });

    const messageInput = document.querySelector(".message-input");
    if (messageInput) {
        const pendingDraft = sessionStorage.getItem(pendingDraftStorageKey);
        if (pendingDraft !== null) {
            messageInput.value = pendingDraft;
            sessionStorage.removeItem(pendingDraftStorageKey);
        }

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
