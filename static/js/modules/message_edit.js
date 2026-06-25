const resizeMessageEditInput = (textarea) => {
    textarea.style.height = "auto";
    textarea.style.height = `${textarea.scrollHeight}px`;
};

const startEditing = (button) => {
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
};

const cancelEditing = (button) => {
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
};

export const initializeMessageEditing = () => {
    document.querySelectorAll("[data-edit-message]").forEach((button) => {
        button.addEventListener("click", () => startEditing(button));
    });

    document.querySelectorAll("[data-cancel-edit]").forEach((button) => {
        button.addEventListener("click", () => cancelEditing(button));
    });

    document.querySelectorAll(".message-edit-input").forEach((textarea) => {
        textarea.addEventListener("input", () => {
            resizeMessageEditInput(textarea);
        });
    });
};
