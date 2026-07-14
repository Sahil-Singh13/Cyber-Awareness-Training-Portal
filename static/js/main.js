// main.js
// -------
// Loaded on EVERY page (see templates/base.html) - this is where truly
// global behavior lives, as opposed to dashboard.js/trainees.js/etc.
// which only load on specific page groups.
//
// VERSION 1.0: the global top loading bar.
//
// WHY HERE AND NOT dashboard.js?
// -------------------------------
// The loading bar has to work on EVERY page, including the login page
// (which does NOT include dashboard.js) - so its controller belongs in
// main.js, the one script base.html guarantees is present everywhere.

(function () {
    const bar = document.getElementById("topLoadingBar");
    if (!bar) {
        return;
    }

    let hideTimeout = null;

    function startLoading() {
        clearTimeout(hideTimeout);
        bar.classList.remove("is-done");
        // Force a reflow so the width transition below actually
        // animates from 0, even if is-loading was already present a
        // moment ago (e.g. rapid double-clicks).
        bar.style.width = "0%";
        // eslint-disable-next-line no-unused-expressions
        bar.offsetWidth;
        bar.classList.add("is-loading");
        // Animate toward (but not all the way to) 100% while we wait -
        // real progress isn't knowable for a normal page navigation, so
        // we fake a satisfying "almost there" creep instead, the same
        // trick used by most real-world top-loading-bar libraries.
        requestAnimationFrame(function () {
            bar.style.width = "80%";
        });
    }

    function finishLoading() {
        bar.style.width = "100%";
        bar.classList.add("is-done");
        hideTimeout = setTimeout(function () {
            bar.classList.remove("is-loading", "is-done");
            bar.style.width = "0%";
        }, 400);
    }

    // ----------------------------------------------------------------
    // TRIGGER 1: full page navigations (clicking a normal link)
    // ----------------------------------------------------------------
    // Only intercept plain left-clicks on same-tab, same-origin links -
    // we don't want to show a loading bar for a ctrl/cmd-click that
    // opens a new tab, an anchor-only "#" link, or an external URL,
    // none of which actually navigate THIS page away.
    document.addEventListener("click", function (event) {
        const link = event.target.closest("a[href]");
        if (!link) return;
        if (event.defaultPrevented || event.button !== 0) return;
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        if (link.target && link.target !== "_self") return;
        if (link.hasAttribute("download")) return;

        const href = link.getAttribute("href") || "";
        if (!href || href.startsWith("#") || href.startsWith("javascript:") || href.startsWith("mailto:")) return;

        try {
            const url = new URL(link.href, window.location.href);
            if (url.origin !== window.location.origin) return;
        } catch (e) {
            return;
        }

        startLoading();
    });

    // ----------------------------------------------------------------
    // TRIGGER 2: form submissions (Add/Edit trainee, login, search...)
    // ----------------------------------------------------------------
    document.addEventListener("submit", function (event) {
        if (event.defaultPrevented) return;
        startLoading();
    });

    // ----------------------------------------------------------------
    // FINISH: the browser has fully loaded the new page
    // ----------------------------------------------------------------
    window.addEventListener("pageshow", finishLoading);

    console.log("Cyber Awareness Training Portal - static/js/main.js loaded successfully.");
})();
