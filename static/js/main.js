const initializeApp = async () => {
    const [
        { initializeChat },
        { initializeConfirmations },
        { initializeMessageEditing },
        { initializeNavigation },
        { initializeThemeToggle },
    ] = await Promise.all([
        import("./modules/chat.js?v=20260625-module-loader"),
        import("./modules/confirmations.js?v=20260625-module-loader"),
        import("./modules/message_edit.js?v=20260625-module-loader"),
        import("./modules/navigation.js?v=20260625-module-loader"),
        import("./modules/theme.js?v=20260625-module-loader"),
    ]);

    initializeThemeToggle();
    initializeConfirmations();
    initializeNavigation();
    initializeChat();
    initializeMessageEditing();
};

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeApp, { once: true });
} else {
    void initializeApp();
}
