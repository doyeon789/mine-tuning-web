const closeCommentMenus = () => {
    document
        .querySelectorAll(".community-comment-menu-panel")
        .forEach((panel) => {
            panel.hidden = true;
            panel
                .closest(".community-comment-menu")
                .querySelector(".community-comment-menu-button")
                .setAttribute("aria-expanded", "false");
        });
};

const initializeLikeForm = () => {
    const likeForm = document.getElementById("community-like-form");
    if (!likeForm) {
        return;
    }

    likeForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const button = document.getElementById("community-like-button");
        const count = document.getElementById("community-like-count");
        const csrfToken = likeForm.querySelector(
            "[name=csrfmiddlewaretoken]",
        ).value;

        button.disabled = true;
        try {
            const response = await fetch(likeForm.action, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            if (!response.ok) {
                likeForm.submit();
                return;
            }

            const data = await response.json();
            button.classList.toggle("is-active", data.is_liked);
            button.querySelector("[data-like-label]").textContent =
                data.is_liked
                    ? button.dataset.likedLabel
                    : button.dataset.unlikedLabel;
            count.textContent = data.like_count;
        } finally {
            button.disabled = false;
        }
    });
};

const initializeCommentMenus = () => {
    document.querySelectorAll(".community-comment-menu").forEach((menu) => {
        const button = menu.querySelector(".community-comment-menu-button");
        const panel = menu.querySelector(".community-comment-menu-panel");

        button.addEventListener("click", (event) => {
            event.stopPropagation();
            const shouldOpen = panel.hidden;

            closeCommentMenus();
            panel.hidden = !shouldOpen;
            button.setAttribute("aria-expanded", String(shouldOpen));
        });
    });

    document.addEventListener("click", closeCommentMenus);
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeCommentMenus();
        }
    });
};

const initializeCommentEditing = () => {
    document
        .querySelectorAll(".community-comment-edit-button")
        .forEach((button) => {
            button.addEventListener("click", () => {
                const comment = button.closest(".community-comment");
                const content = comment.querySelector(
                    ".community-comment-content",
                );
                const form = comment.querySelector(
                    ".community-comment-edit-form",
                );
                const textarea = form.querySelector("textarea");

                content.hidden = true;
                form.hidden = false;
                textarea.focus();
                textarea.setSelectionRange(
                    textarea.value.length,
                    textarea.value.length,
                );
            });
        });

    document
        .querySelectorAll(".community-comment-edit-cancel")
        .forEach((button) => {
            button.addEventListener("click", () => {
                const comment = button.closest(".community-comment");

                comment.querySelector(
                    ".community-comment-content",
                ).hidden = false;
                comment.querySelector(
                    ".community-comment-edit-form",
                ).hidden = true;
            });
        });
};

initializeLikeForm();
initializeCommentMenus();
initializeCommentEditing();
