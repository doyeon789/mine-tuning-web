export const initializeThemeToggle = () => {
    const themeToggle = document.querySelector("[data-theme-toggle]");
    if (!themeToggle) {
        return;
    }

    const syncThemeToggle = () => {
        const isDark = document.documentElement.dataset.theme === "dark";
        themeToggle.setAttribute("aria-pressed", String(isDark));
        themeToggle.setAttribute(
            "aria-label",
            isDark ? "라이트 모드로 전환" : "다크 모드로 전환",
        );
    };

    syncThemeToggle();
    themeToggle.addEventListener("click", () => {
        const nextTheme =
            document.documentElement.dataset.theme === "dark"
                ? "light"
                : "dark";
        document.documentElement.dataset.theme = nextTheme;
        localStorage.setItem("mine-tuning-theme", nextTheme);
        syncThemeToggle();
    });
};
