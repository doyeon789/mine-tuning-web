const initializeApp = async () => {
    const [
        { initializeChat },
        { initializeConfirmations },
        { initializeMessageEditing },
        { initializeNavigation },
        { initializeThemeToggle },
    ] = await Promise.all([
        import("./modules/chat.js?v=20260625-sidebar-refresh"),
        import("./modules/confirmations.js?v=20260625-sidebar-refresh"),
        import("./modules/message_edit.js?v=20260625-sidebar-refresh"),
        import("./modules/navigation.js?v=20260625-sidebar-refresh"),
        import("./modules/theme.js?v=20260625-sidebar-refresh"),
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
