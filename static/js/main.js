import { initializeChat } from "./modules/chat.js";
import { initializeConfirmations } from "./modules/confirmations.js";
import { initializeMessageEditing } from "./modules/message_edit.js";
import { initializeNavigation } from "./modules/navigation.js";
import { initializeThemeToggle } from "./modules/theme.js";

const initializeApp = () => {
    initializeThemeToggle();
    initializeConfirmations();
    initializeNavigation();
    initializeChat();
    initializeMessageEditing();
};

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeApp, { once: true });
} else {
    initializeApp();
}
