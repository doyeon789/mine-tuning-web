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
            if (shouldOpen) {
                const input = menu.querySelector("input");
                input.focus();
                input.select();
            }
        });
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest("[data-history-item]")) {
            closeHistoryMenus();
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
            const textWidth = text.getBoundingClientRect().width;

            message.style.width = `${textWidth}px`;
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

    const markdownEditor = document.querySelector("[data-markdown-editor]");
    if (markdownEditor) {
        const textarea = markdownEditor.querySelector("textarea");
        const status = markdownEditor.querySelector("[data-image-upload-status]");
        const uploadUrl = markdownEditor.dataset.imageUploadUrl;
        const csrfToken = markdownEditor
            .closest("form")
            .querySelector("[name=csrfmiddlewaretoken]").value;
        const allowedImageTypes = [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
        ];
        const maxImageSize = 5 * 1024 * 1024;
        let dragDepth = 0;

        const showUploadStatus = (message, isError = false) => {
            status.textContent = message;
            status.classList.toggle("error", isError);
        };

        const insertMarkdownAtCursor = (markdown) => {
            const start = textarea.selectionStart;
            const end = textarea.selectionEnd;
            const before = textarea.value.slice(0, start);
            const after = textarea.value.slice(end);
            const prefix = before && !before.endsWith("\n") ? "\n" : "";
            const suffix = after && !after.startsWith("\n") ? "\n" : "";
            const insertedText = prefix + markdown + suffix;

            textarea.value = before + insertedText + after;
            const cursorPosition = before.length + insertedText.length;
            textarea.focus();
            textarea.setSelectionRange(cursorPosition, cursorPosition);
            textarea.dispatchEvent(new Event("input", { bubbles: true }));
        };

        const imageAltText = (fileName) => {
            const withoutExtension = fileName.replace(/\.[^.]+$/, "");
            return withoutExtension.replace(/[\[\]]/g, "").trim() || "이미지";
        };

        const uploadImage = async (file) => {
            if (!allowedImageTypes.includes(file.type)) {
                throw new Error("PNG, JPEG, GIF, WEBP 이미지만 사용할 수 있습니다.");
            }
            if (file.size > maxImageSize) {
                throw new Error("이미지는 최대 5MB까지 업로드할 수 있습니다.");
            }

            showUploadStatus(file.name + " 업로드 중...");

            const formData = new FormData();
            formData.append("image", file);

            const response = await fetch(uploadUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                },
                body: formData,
            });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "이미지 업로드에 실패했습니다.");
            }

            const markdown =
                "![" + imageAltText(file.name) + "](" + data.url + ")";
            insertMarkdownAtCursor(markdown);
            showUploadStatus(file.name + " 이미지 삽입 완료");
        };

        const uploadImages = async (files) => {
            for (const file of files) {
                try {
                    await uploadImage(file);
                } catch (error) {
                    showUploadStatus(error.message, true);
                    break;
                }
            }
        };

        markdownEditor.addEventListener("dragenter", (event) => {
            if (!event.dataTransfer.types.includes("Files")) {
                return;
            }
            event.preventDefault();
            dragDepth += 1;
            markdownEditor.classList.add("dragging");
        });

        markdownEditor.addEventListener("dragover", (event) => {
            if (!event.dataTransfer.types.includes("Files")) {
                return;
            }
            event.preventDefault();
            event.dataTransfer.dropEffect = "copy";
        });

        markdownEditor.addEventListener("dragleave", () => {
            dragDepth = Math.max(0, dragDepth - 1);
            if (dragDepth === 0) {
                markdownEditor.classList.remove("dragging");
            }
        });

        markdownEditor.addEventListener("drop", (event) => {
            event.preventDefault();
            dragDepth = 0;
            markdownEditor.classList.remove("dragging");

            const imageFiles = Array.from(event.dataTransfer.files).filter(
                (file) => allowedImageTypes.includes(file.type)
            );
            if (!imageFiles.length) {
                showUploadStatus("지원하는 이미지 파일을 드롭해 주세요.", true);
                return;
            }
            uploadImages(imageFiles);
        });

        textarea.addEventListener("paste", (event) => {
            const imageFiles = Array.from(event.clipboardData.items)
                .filter(
                    (item) =>
                        item.kind === "file" &&
                        allowedImageTypes.includes(item.type)
                )
                .map((item) => item.getAsFile())
                .filter(Boolean);

            if (!imageFiles.length) {
                return;
            }

            event.preventDefault();
            uploadImages(imageFiles);
        });
    }});

