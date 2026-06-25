(() => {
    const storedTheme = localStorage.getItem("mine-tuning-theme");
    const prefersDark = window.matchMedia(
        "(prefers-color-scheme: dark)",
    ).matches;
    const theme = storedTheme || (prefersDark ? "dark" : "light");
    document.documentElement.dataset.theme = theme;
})();
