document.addEventListener("DOMContentLoaded", () => {
    const DRAFT_KEY = "mine-chat-pending-draft";
    const MAX_INPUT_HEIGHT = 240;
    let responsePending = false;

    const all = (selector, root = document) => [...root.querySelectorAll(selector)];

    const scrollToBottom = (root = document) => {
        const container = root.querySelector("[data-message-scroll]");
        if (container) container.scrollTop = container.scrollHeight;
    };

    const resizeComposer = (textarea) => {
        textarea.style.height = "auto";
        textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_INPUT_HEIGHT)}px`;
        textarea.style.overflowY =
            textarea.scrollHeight > MAX_INPUT_HEIGHT ? "auto" : "hidden";
    };

    const resizeEditor = (textarea) => {
        textarea.style.height = "auto";
        textarea.style.height = `${textarea.scrollHeight}px`;
    };

    const saveDraft = (textarea) => {
        if (textarea.dataset.preserveDraft !== "true") return;
        if (textarea.value) sessionStorage.setItem(DRAFT_KEY, textarea.value);
        else sessionStorage.removeItem(DRAFT_KEY);
    };

    const restoreDraft = (textarea) => {
        const draft = sessionStorage.getItem(DRAFT_KEY);
        if (draft !== null) {
            textarea.value = draft;
            sessionStorage.removeItem(DRAFT_KEY);
        }
        resizeComposer(textarea);
    };

    const closeHistoryMenus = () => {
        all("[data-history-menu]").forEach((menu) => {
            menu.hidden = true;
            const item = menu.closest("[data-history-item]");
            const title = item?.querySelector("[data-history-title-textarea]");
            const rename = menu.querySelector("[data-history-rename-button]");
            if (title) {
                title.readOnly = true;
                title.value = title.defaultValue;
            }
            if (rename) rename.hidden = false;
        });
        all("[data-history-menu-button]").forEach((button) => {
            button.setAttribute("aria-expanded", "false");
        });
    };

    const closeAccountMenu = () => {
        const menu = document.querySelector("[data-account-menu]");
        const button = document.querySelector("[data-account-menu-button]");
        if (!menu || !button) return;
        menu.hidden = true;
        button.setAttribute("aria-expanded", "false");
    };

    const replaceChatApp = (html, url) => {
        const current = document.querySelector("[data-chat-app]");
        if (!current) return;

        const template = document.createElement("template");
        template.innerHTML = html.trim();
        const next = template.content.querySelector("[data-chat-app]");
        if (!next) return;

        current.replaceWith(next);
        if (url) window.history.replaceState({}, "", url);
        initializeChatApp(next);
    };

    const submitHistoryForm = async (form) => {
        if (form.dataset.submitting === "true") return;
        if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) return;

        form.dataset.submitting = "true";
        form.setAttribute("aria-busy", "true");
        all("button[type='submit']", form).forEach((button) => {
            button.disabled = true;
        });

        try {
            const app = form.closest("[data-chat-app]");
            const headers = { "X-Requested-With": "XMLHttpRequest" };
            if (app?.dataset.activeSessionId) {
                headers["X-Active-Session"] = app.dataset.activeSessionId;
            }

            const response = await fetch(form.action, {
                method: form.method || "POST",
                body: new FormData(form),
                headers,
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "요청 처리 실패");
            if (data.app_html) replaceChatApp(data.app_html, data.url);
        } catch {
            form.submit();
        } finally {
            form.dataset.submitting = "false";
            form.removeAttribute("aria-busy");
            all("button[type='submit']", form).forEach((button) => {
                button.disabled = false;
            });
        }
    };

    const showPendingResponse = (content, showUserMessage) => {
        const host = document.querySelector("[data-pending-response-host]");
        if (!host || host.querySelector("[data-pending-response]")) return;
        host.querySelector(".empty-state")?.remove();

        if (showUserMessage) {
            const message = document.createElement("article");
            const body = document.createElement("div");
            message.className = "message user pending-user-message";
            body.className = "message-content";
            body.textContent = content;
            message.appendChild(body);
            host.appendChild(message);
        }

        const pending = document.createElement("article");
        pending.className = "message assistant pending-response";
        pending.dataset.pendingResponse = "";
        pending.setAttribute("role", "status");
        pending.setAttribute("aria-live", "polite");
        pending.innerHTML = `
            <div class="message-content pending-response-content">
                <span>답변 생성 중</span>
                <span class="pending-response-dots" aria-hidden="true">
                    <span></span><span></span><span></span>
                </span>
            </div>`;
        host.hidden = false;
        host.appendChild(pending);
        scrollToBottom();
    };

    const finishEdit = (form, content) => {
        if (!form.matches("[data-message-form]")) return;
        const message = form.closest(".message");
        const text = form.querySelector("[data-message-text]");
        const textarea = form.querySelector("textarea");
        const edit = form.querySelector("[data-edit-message]");
        const save = form.querySelector(".message-edit-button");
        const cancel = form.querySelector("[data-cancel-edit]");

        message?.classList.remove("editing");
        if (message) message.style.width = "";
        if (text) {
            text.textContent = content;
            text.hidden = false;
        }
        if (textarea) textarea.hidden = true;
        if (save) save.hidden = true;
        if (cancel) cancel.hidden = true;
        if (edit) {
            edit.hidden = false;
            edit.disabled = true;
        }
    };

    const removeFollowingMessages = (form) => {
        if (!form.matches("[data-message-form]")) return;
        let next = form.closest(".message")?.nextElementSibling;
        while (next) {
            const current = next;
            next = next.nextElementSibling;
            current.remove();
        }
    };

    const preserveComposerDraft = () => {
        const input = document.querySelector(".message-input");
        if (!input) return;
        input.dataset.preserveDraft = "true";
        saveDraft(input);
    };

    const clearComposerForSubmission = (form, input) => {
        const hidden = document.createElement("input");
        hidden.type = "hidden";
        hidden.name = "content";
        hidden.value = input.value;
        form.appendChild(hidden);

        input.removeAttribute("name");
        input.required = false;
        input.value = "";
        input.dataset.preserveDraft = "true";
        sessionStorage.removeItem(DRAFT_KEY);
        resizeComposer(input);
    };

    const setSubmittingUi = (form) => {
        all("[data-chat-submit-form] button[type='submit']").forEach((button) => {
            button.disabled = true;
        });

        const button = form.querySelector("button[type='submit']");
        if (button) {
            button.classList.add("is-loading");
            button.setAttribute("aria-label", "답변 생성 중");
            if (!button.classList.contains("send-button")) {
                button.textContent = "생성 중...";
            }
        }

        const firstChat = document.querySelector("[data-first-chat]");
        if (firstChat) {
            firstChat.classList.add("is-submitting");
            document.querySelector("[data-first-chat-heading]")?.setAttribute("hidden", "");
            document.querySelector("[data-example-questions]")?.setAttribute("hidden", "");
        }
    };

    const submitChatForm = async (form) => {
        try {
            const response = await fetch(form.action, {
                method: form.method || "POST",
                body: new FormData(form),
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || "요청을 처리하지 못했습니다.");
            }
            if (!data.app_html) {
                throw new Error("채팅 화면을 불러오지 못했습니다.");
            }
            responsePending = false;
            replaceChatApp(data.app_html, data.url);
        } catch (error) {
            responsePending = false;
            form.dataset.submitting = "false";
            form.removeAttribute("aria-busy");
            alert(error.message || "채팅 요청에 실패했습니다.");
        }
    };

    const handleChatSubmit = (event) => {
        const form = event.currentTarget;
        if (responsePending || form.dataset.submitting === "true") {
            event.preventDefault();
            return;
        }

        const input = form.querySelector("[name='content']");
        if (!input || !input.value.trim()) {
            event.preventDefault();
            return;
        }

        event.preventDefault();
        const content = input.value.trim();
        responsePending = true;
        form.dataset.submitting = "true";
        form.setAttribute("aria-busy", "true");

        if (input.classList.contains("message-input")) {
            clearComposerForSubmission(form, input);
        } else if (input instanceof HTMLTextAreaElement) {
            input.readOnly = true;
            preserveComposerDraft();
        }

        finishEdit(form, content);
        removeFollowingMessages(form);
        setSubmittingUi(form);
        showPendingResponse(content, !form.matches("[data-message-form]"));
        submitChatForm(form);
    };

    const startEdit = (button) => {
        const form = button.closest("[data-message-form]");
        const message = form?.closest(".message");
        const text = form?.querySelector("[data-message-text]");
        const textarea = form?.querySelector("textarea");
        const save = form?.querySelector(".message-edit-button");
        const cancel = form?.querySelector("[data-cancel-edit]");
        if (!message || !text || !textarea) return;

        message.classList.add("editing");
        text.hidden = true;
        textarea.hidden = false;
        resizeEditor(textarea);
        button.hidden = true;
        if (save) save.hidden = false;
        if (cancel) cancel.hidden = false;
        textarea.focus();
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    };

    const cancelEdit = (button) => {
        const form = button.closest("[data-message-form]");
        const message = form?.closest(".message");
        const text = form?.querySelector("[data-message-text]");
        const textarea = form?.querySelector("textarea");
        const edit = form?.querySelector("[data-edit-message]");
        const save = form?.querySelector(".message-edit-button");
        if (!message || !text || !textarea) return;

        message.classList.remove("editing");
        message.style.width = "";
        textarea.value = textarea.defaultValue;
        textarea.style.height = "";
        textarea.hidden = true;
        text.hidden = false;
        if (save) save.hidden = true;
        button.hidden = true;
        if (edit) edit.hidden = false;
    };

    const bindHistory = (root) => {
        all("[data-history-menu-button]", root).forEach((button) => {
            button.addEventListener("click", (event) => {
                event.stopPropagation();
                const menu = button.closest("[data-history-item]")?.querySelector("[data-history-menu]");
                if (!menu) return;
                const open = menu.hidden;
                closeHistoryMenus();
                menu.hidden = !open;
                button.setAttribute("aria-expanded", String(open));
            });
        });

        all("[data-history-rename-button]", root).forEach((button) => {
            button.addEventListener("click", (event) => {
                event.stopPropagation();
                const title = button.closest("[data-history-item]")?.querySelector("[data-history-title-textarea]");
                if (!title) return;
                closeHistoryMenus();
                button.hidden = true;
                title.readOnly = false;
                title.focus();
                title.select();
            });
        });

        all("[data-history-title-form]", root).forEach((form) => {
            const title = form.querySelector("[data-history-title-textarea]");
            if (!title) return;
            title.addEventListener("click", () => {
                if (title.readOnly) window.location.href = form.dataset.sessionUrl;
            });
            title.addEventListener("keydown", (event) => {
                if (event.key === "Escape") {
                    event.preventDefault();
                    title.value = title.defaultValue;
                    closeHistoryMenus();
                } else if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    form.requestSubmit();
                }
            });
        });

        all("[data-history-ajax-form]", root).forEach((form) => {
            form.addEventListener("submit", (event) => {
                event.preventDefault();
                submitHistoryForm(form);
            });
        });
    };

    const bindComposer = (root) => {
        all(".message-input", root).forEach((textarea) => {
            resizeComposer(textarea);
            textarea.addEventListener("input", () => {
                resizeComposer(textarea);
                saveDraft(textarea);
            });
            textarea.addEventListener("keydown", (event) => {
                if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
                event.preventDefault();
                const form = textarea.closest("form");
                if (form && textarea.value.trim()) form.requestSubmit();
            });
        });

        all("[data-chat-submit-form]", root).forEach((form) => {
            form.addEventListener("submit", handleChatSubmit);
        });

        const input = root.querySelector(".message-input");
        if (input) {
            restoreDraft(input);
            input.focus();
            input.setSelectionRange(input.value.length, input.value.length);
        }
    };

    const initializeChatApp = (root = document) => {
        scrollToBottom(root);

        all("[data-confirm]:not([data-history-ajax-form])", root).forEach((form) => {
            form.addEventListener("submit", (event) => {
                if (!window.confirm(form.dataset.confirm)) event.preventDefault();
            });
        });

        bindHistory(root);
        bindComposer(root);

        const accountButton = root.querySelector("[data-account-menu-button]");
        accountButton?.addEventListener("click", (event) => {
            event.stopPropagation();
            const menu = root.querySelector("[data-account-menu]");
            if (!menu) return;
            const open = menu.hidden;
            closeHistoryMenus();
            menu.hidden = !open;
            accountButton.setAttribute("aria-expanded", String(open));
        });

        all("[data-edit-message]", root).forEach((button) => {
            button.addEventListener("click", () => startEdit(button));
        });
        all("[data-cancel-edit]", root).forEach((button) => {
            button.addEventListener("click", () => cancelEdit(button));
        });
        all(".message-edit-input", root).forEach((textarea) => {
            textarea.addEventListener("input", () => resizeEditor(textarea));
        });
    };

    document.addEventListener("click", (event) => {
        if (!event.target.closest("[data-history-item]")) closeHistoryMenus();
        if (!event.target.closest("[data-account-menu-wrap]")) closeAccountMenu();
    });

    document.addEventListener("keydown", (event) => {
        const input = document.querySelector(".message-input");
        const target = event.target;
        const editable =
            target instanceof HTMLInputElement ||
            target instanceof HTMLTextAreaElement ||
            target instanceof HTMLSelectElement ||
            target.isContentEditable;
        if (!input || editable || event.ctrlKey || event.metaKey || event.altKey || event.key.length !== 1) return;
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
    });

    initializeChatApp();
});
