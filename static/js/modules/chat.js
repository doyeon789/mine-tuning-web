const PENDING_DRAFT_STORAGE_KEY = "mine-chat-pending-draft";
const MESSAGE_INPUT_MAX_HEIGHT = 240;

const scrollMessagesToBottom = () => {
    const messageScroll = document.querySelector("[data-message-scroll]");
    if (messageScroll) {
        messageScroll.scrollTop = messageScroll.scrollHeight;
    }
};

const resizeMessageInput = (textarea) => {
    textarea.style.height = "auto";
    textarea.style.height =
        `${Math.min(textarea.scrollHeight, MESSAGE_INPUT_MAX_HEIGHT)}px`;
    textarea.style.overflowY =
        textarea.scrollHeight > MESSAGE_INPUT_MAX_HEIGHT ? "auto" : "hidden";
};

const initializeMessageInputs = () => {
    document.querySelectorAll(".message-input").forEach((textarea) => {
        resizeMessageInput(textarea);

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
            resizeMessageInput(textarea);

            if (textarea.dataset.preserveDraft !== "true") {
                return;
            }

            if (textarea.value) {
                sessionStorage.setItem(
                    PENDING_DRAFT_STORAGE_KEY,
                    textarea.value,
                );
            } else {
                sessionStorage.removeItem(PENDING_DRAFT_STORAGE_KEY);
            }
        });
    });
};

const showPendingResponse = (content, showUserMessage) => {
    const host = document.querySelector("[data-pending-response-host]");
    if (!host || host.querySelector("[data-pending-response]")) {
        return;
    }

    host.querySelector(".empty-state")?.remove();

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
    scrollMessagesToBottom();
};

const disableChatSubmitButtons = () => {
    document.querySelectorAll("[data-chat-submit-form]").forEach((form) => {
        form.querySelectorAll("button[type='submit']").forEach((button) => {
            button.disabled = true;
        });
    });
};

const clearSubmittedMessageInput = (form, contentInput) => {
    const submittedContentInput = document.createElement("input");
    submittedContentInput.type = "hidden";
    submittedContentInput.name = "content";
    submittedContentInput.value = contentInput.value;
    form.appendChild(submittedContentInput);

    contentInput.removeAttribute("name");
    contentInput.required = false;
    contentInput.value = "";
    resizeMessageInput(contentInput);
    contentInput.dataset.preserveDraft = "true";
    sessionStorage.removeItem(PENDING_DRAFT_STORAGE_KEY);
};

const setSubmittingLayout = () => {
    const firstChat = document.querySelector("[data-first-chat]");
    if (!firstChat) {
        return;
    }

    firstChat.classList.add("is-submitting");
    document
        .querySelector("[data-first-chat-heading]")
        ?.setAttribute("hidden", "");
    document
        .querySelector("[data-example-questions]")
        ?.setAttribute("hidden", "");
};

const setSubmitButtonLoading = (form) => {
    const submitButton = form.querySelector("button[type='submit']");
    if (!submitButton) {
        return;
    }

    submitButton.classList.add("is-loading");
    submitButton.setAttribute("aria-label", "답변 생성 중");
    if (!submitButton.classList.contains("send-button")) {
        submitButton.textContent = "생성 중...";
    }
};

const initializeChatForms = () => {
    document.querySelectorAll("[data-chat-submit-form]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (
                event.defaultPrevented ||
                event.submitter?.matches("[data-message-delete]")
            ) {
                return;
            }

            if (form.dataset.submitting === "true") {
                event.preventDefault();
                return;
            }

            const contentInput = form.querySelector("[name='content']");
            if (!contentInput || !contentInput.value.trim()) {
                event.preventDefault();
                return;
            }

            const submittedContent = contentInput.value.trim();
            form.dataset.submitting = "true";
            form.setAttribute("aria-busy", "true");
            disableChatSubmitButtons();

            if (contentInput.classList.contains("message-input")) {
                clearSubmittedMessageInput(form, contentInput);
            } else if (contentInput instanceof HTMLTextAreaElement) {
                contentInput.readOnly = true;
            }

            setSubmittingLayout();
            setSubmitButtonLoading(form);
            showPendingResponse(
                submittedContent,
                !form.matches("[data-message-form]"),
            );
        });
    });
};

const initializePrimaryMessageInput = () => {
    const messageInput = document.querySelector(".message-input");
    if (!messageInput) {
        return;
    }

    const pendingDraft = sessionStorage.getItem(PENDING_DRAFT_STORAGE_KEY);
    if (pendingDraft !== null) {
        messageInput.value = pendingDraft;
        sessionStorage.removeItem(PENDING_DRAFT_STORAGE_KEY);
    }

    resizeMessageInput(messageInput);
    messageInput.focus();
    messageInput.setSelectionRange(
        messageInput.value.length,
        messageInput.value.length,
    );

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
        messageInput.setSelectionRange(
            messageInput.value.length,
            messageInput.value.length,
        );
    });
};

export const initializeChat = () => {
    scrollMessagesToBottom();
    initializeMessageInputs();
    initializeChatForms();
    initializePrimaryMessageInput();
};
