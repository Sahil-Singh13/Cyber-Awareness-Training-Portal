// dashboard.js
// ------------
// Behavior shared by every dashboard-area page:
//   1. Responsive sidebar (open/close on mobile)
//   2. Dark mode toggle + persistence (localStorage)
//   3. Bootstrap tooltip activation (for disabled nav links/buttons)
//   4. Toast auto-show for flashed messages
//   5. Chart.js dashboard charts (called from dashboard.html directly,
//      with the actual numbers, since only dashboard.html has them)

document.addEventListener("DOMContentLoaded", function () {

    // ----------------------------------------------------------------
    // 1. RESPONSIVE SIDEBAR
    // ----------------------------------------------------------------
    const sidebar = document.getElementById("sidebar");
    const sidebarToggleBtn = document.getElementById("sidebarToggleBtn");
    const sidebarBackdrop = document.getElementById("sidebarBackdrop");

    function openSidebar() {
        sidebar.classList.add("sidebar-open");
        sidebarBackdrop.classList.add("show");
    }

    function closeSidebar() {
        sidebar.classList.remove("sidebar-open");
        sidebarBackdrop.classList.remove("show");
    }

    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener("click", function () {
            // On desktop widths the sidebar is always visible via CSS,
            // so this toggle only has a visible effect below the
            // 991.98px breakpoint defined in dashboard.css - clicking
            // it on desktop is harmless (classList changes with no
            // visual effect since .sidebar-open only matters inside
            // that same media query).
            if (sidebar.classList.contains("sidebar-open")) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });
    }

    // Clicking the dark backdrop (the dimmed area beside the open
    // mobile sidebar) closes it again - standard off-canvas UX.
    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener("click", closeSidebar);
    }

    // ----------------------------------------------------------------
    // 2. DARK MODE TOGGLE
    // ----------------------------------------------------------------
    // Note: the SAVED preference was already applied before this file
    // even loaded (see the inline script in dashboard_layout.html) -
    // this block only handles what happens when the admin actively
    // clicks the toggle button.
    const themeToggleBtn = document.getElementById("themeToggleBtn");
    const themeToggleIcon = document.getElementById("themeToggleIcon");

    function updateThemeIcon(theme) {
        if (!themeToggleIcon) return;
        themeToggleIcon.classList.toggle("bi-moon-stars-fill", theme === "light");
        themeToggleIcon.classList.toggle("bi-brightness-high-fill", theme === "dark");
    }

    // Set the icon correctly on page load too, matching whatever theme
    // the inline script already applied to <html data-theme="...">.
    updateThemeIcon(document.documentElement.getAttribute("data-theme") || "light");

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener("click", function () {
            const current = document.documentElement.getAttribute("data-theme") || "light";
            const next = current === "light" ? "dark" : "light";

            document.documentElement.setAttribute("data-theme", next);
            // localStorage persists across page refreshes AND across
            // browser restarts (unlike sessionStorage), which is
            // exactly the "remember theme after refresh" requirement.
            localStorage.setItem("theme", next);
            updateThemeIcon(next);
        });
    }

    // ----------------------------------------------------------------
    // 3. BOOTSTRAP TOOLTIPS
    // ----------------------------------------------------------------
    // Bootstrap 5 requires tooltips to be manually initialized - it
    // won't activate every [data-bs-toggle="tooltip"] element
    // automatically. This finds all of them (disabled sidebar links,
    // disabled quick-action buttons, the theme toggle, logout button)
    // and turns each into a working Bootstrap Tooltip instance.
    const tooltipTriggers = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggers.forEach(function (el) {
        new bootstrap.Tooltip(el);
    });

    // ----------------------------------------------------------------
    // 4. TOAST NOTIFICATIONS
    // ----------------------------------------------------------------
    // Bootstrap toasts are hidden by default until we explicitly call
    // .show() on each one - this finds every toast rendered by
    // partials/_toasts.html (i.e. any flash() message from the current
    // request) and pops it up automatically, with Bootstrap's built-in
    // auto-hide behavior after a few seconds.
    const toastElements = document.querySelectorAll(".app-toast");
    toastElements.forEach(function (el) {
        const toast = new bootstrap.Toast(el, { delay: 4000 });
        toast.show();
    });
});

// ----------------------------------------------------------------
// 5. CHART.JS DASHBOARD CHARTS
// ----------------------------------------------------------------
// Defined as a standalone function (not inside DOMContentLoaded above)
// because dashboard.html calls it directly, passing in the real
// server-computed numbers, right after this script tag loads. Keeping
// it separate from the generic sidebar/theme/tooltip setup above means
// pages that DON'T have charts never need to call this function at
// all - dashboard.js stays useful to every dashboard-area page, while
// this piece is opt-in.
function initDashboardCharts(data) {
    // Respect the current theme so chart text/gridlines stay readable
    // in both light and dark mode.
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const gridColor = isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)";
    const textColor = isDark ? "#9aa7b8" : "#6b7280";

    Chart.defaults.color = textColor;
    Chart.defaults.font.family = "'Segoe UI', system-ui, -apple-system, sans-serif";

    // ---- Chart 1: Training Progress (completed vs pending donut) ----
    const progressCanvas = document.getElementById("progressChart");
    if (progressCanvas) {
        new Chart(progressCanvas, {
            type: "doughnut",
            data: {
                labels: ["Completed", "Pending"],
                datasets: [{
                    data: [data.completedVsPending.completed, data.completedVsPending.pending],
                    backgroundColor: ["#0d6efd", isDark ? "#263140" : "#e9edf3"],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "70%",
                plugins: { legend: { position: "bottom" } }
            }
        });
    }

    // ---- Chart 2: Male vs Female (vs Other) ----
    const genderCanvas = document.getElementById("genderChart");
    if (genderCanvas) {
        new Chart(genderCanvas, {
            type: "pie",
            data: {
                labels: Object.keys(data.genderCounts),
                datasets: [{
                    data: Object.values(data.genderCounts),
                    backgroundColor: ["#0d6efd", "#e83e8c", "#ffc107"],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: "bottom" } }
            }
        });
    }

    // ---- Chart 3: Daily Training Count ----
    const dailyCanvas = document.getElementById("dailyChart");
    if (dailyCanvas) {
        new Chart(dailyCanvas, {
            type: "bar",
            data: {
                labels: data.dailyLabels,
                datasets: [{
                    label: "People Trained",
                    data: data.dailyCounts,
                    backgroundColor: "#0d6efd",
                    borderRadius: 6,
                    maxBarThickness: 34
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false } },
                    y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: gridColor } }
                }
            }
        });
    }
}
