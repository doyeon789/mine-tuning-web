(() => {
    const initializeMarkdownImageUpload = () => {
        const editor = document.querySelector("[data-markdown-editor]");
        if (!editor) {
            return;
        }

        const textarea = editor.querySelector("textarea");
        const status = editor.querySelector("[data-image-upload-status]");
        const uploadUrl = editor.dataset.imageUploadUrl;
        const form = editor.closest("form");
        const csrfInput = form && form.querySelector(
            "[name=csrfmiddlewaretoken]"
        );

        if (!textarea || !status || !uploadUrl || !csrfInput) {
            return;
        }

        const allowedImageTypes = new Set([
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
        ]);
        const maxImageSize = 5 * 1024 * 1024;

        const containsFiles = (event) => {
            if (!event.dataTransfer) {
                return false;
            }
            return Array.from(event.dataTransfer.types || []).includes(
                "Files"
            );
        };

        const showStatus = (message, isError = false) => {
            status.textContent = message;
            status.classList.toggle("error", isError);
        };

        const insertAtCursor = (markdown) => {
            const start = textarea.selectionStart;
            const end = textarea.selectionEnd;
            const before = textarea.value.slice(0, start);
            const after = textarea.value.slice(end);
            const prefix = before && !before.endsWith("\n") ? "\n" : "";
            const suffix = after && !after.startsWith("\n") ? "\n" : "";
            const inserted = prefix + markdown + suffix;

            textarea.value = before + inserted + after;
            const cursor = before.length + inserted.length;
            textarea.focus();
            textarea.setSelectionRange(cursor, cursor);
            textarea.dispatchEvent(new Event("input", { bubbles: true }));
        };

        const makeAltText = (fileName) => {
            const withoutExtension = fileName.replace(/\.[^.]+$/, "");
            return withoutExtension
                .replace(/[\[\]]/g, "")
                .trim() || "이미지";
        };

        const uploadImage = async (file) => {
            if (!allowedImageTypes.has(file.type)) {
                throw new Error(
                    "PNG, JPEG, GIF, WEBP 이미지만 사용할 수 있습니다."
                );
            }
            if (file.size > maxImageSize) {
                throw new Error(
                    "이미지는 최대 5MB까지 업로드할 수 있습니다."
                );
            }

            showStatus(file.name + " 업로드 중...");

            const formData = new FormData();
            formData.append("image", file);

            const response = await fetch(uploadUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfInput.value,
                },
                body: formData,
            });
            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                throw new Error(
                    data.error || "이미지 업로드에 실패했습니다."
                );
            }

            const markdown =
                "![" + makeAltText(file.name) + "](" + data.url + ")";
            insertAtCursor(markdown);
            showStatus(file.name + " 이미지 삽입 완료");
        };

        const uploadImages = async (files) => {
            for (const file of files) {
                try {
                    await uploadImage(file);
                } catch (error) {
                    showStatus(
                        error instanceof Error
                            ? error.message
                            : "이미지 업로드에 실패했습니다.",
                        true
                    );
                    return;
                }
            }
        };

        const handleDragOver = (event) => {
            if (!containsFiles(event)) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            event.dataTransfer.dropEffect = "copy";
            editor.classList.add("dragging");
        };

        const handleDrop = (event) => {
            if (!containsFiles(event)) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            editor.classList.remove("dragging");

            const files = Array.from(event.dataTransfer.files);
            const imageFiles = files.filter((file) =>
                allowedImageTypes.has(file.type)
            );

            if (!imageFiles.length) {
                showStatus(
                    "PNG, JPEG, GIF, WEBP 이미지를 내용 영역에 드롭해 주세요.",
                    true
                );
                return;
            }

            uploadImages(imageFiles);
        };

        editor.addEventListener("dragenter", handleDragOver, true);
        editor.addEventListener("dragover", handleDragOver, true);
        editor.addEventListener("drop", handleDrop, true);
        editor.addEventListener(
            "dragleave",
            (event) => {
                if (
                    event.relatedTarget &&
                    editor.contains(event.relatedTarget)
                ) {
                    return;
                }
                editor.classList.remove("dragging");
            },
            true
        );

        textarea.addEventListener("paste", (event) => {
            const items = event.clipboardData
                ? Array.from(event.clipboardData.items)
                : [];
            const imageFiles = items
                .filter(
                    (item) =>
                        item.kind === "file" &&
                        allowedImageTypes.has(item.type)
                )
                .map((item) => item.getAsFile())
                .filter(Boolean);

            if (!imageFiles.length) {
                return;
            }

            event.preventDefault();
            uploadImages(imageFiles);
        });

        document.addEventListener(
            "drop",
            (event) => {
                if (containsFiles(event) && !editor.contains(event.target)) {
                    event.preventDefault();
                }
            },
            true
        );
        document.addEventListener(
            "dragover",
            (event) => {
                if (containsFiles(event) && !editor.contains(event.target)) {
                    event.preventDefault();
                }
            },
            true
        );
    };

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initializeMarkdownImageUpload,
            { once: true }
        );
    } else {
        initializeMarkdownImageUpload();
    }
})();
