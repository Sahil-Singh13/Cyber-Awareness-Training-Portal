// auth.js
// -------
// Small, self-contained behaviors for the login page only:
//   1. Password show/hide toggle
//   2. Loading spinner on the Login button while the form submits
//
// Loaded only on login.html via {% block extra_scripts %}, so it never
// adds unnecessary weight to other pages.

document.addEventListener("DOMContentLoaded", function () {

    // ----------------------------------------------------------------
    // 1. PASSWORD SHOW / HIDE TOGGLE
    // ----------------------------------------------------------------
    const toggleBtn = document.getElementById("togglePassword");
    const passwordInput = document.getElementById("passwordInput");
    const toggleIcon = document.getElementById("togglePasswordIcon");

    if (toggleBtn && passwordInput && toggleIcon) {
        toggleBtn.addEventListener("click", function () {
            // Flip the input's type between "password" (dots/asterisks)
            // and "text" (plain readable characters).
            const isHidden = passwordInput.getAttribute("type") === "password";
            passwordInput.setAttribute("type", isHidden ? "text" : "password");

            // Swap the eye icon to match the new state, so the button
            // itself communicates what clicking it will do next.
            toggleIcon.classList.toggle("bi-eye-fill", !isHidden);
            toggleIcon.classList.toggle("bi-eye-slash-fill", isHidden);
        });
    }

    // ----------------------------------------------------------------
    // 2. LOADING BUTTON ANIMATION ON SUBMIT
    // ----------------------------------------------------------------
    const loginForm = document.getElementById("loginForm");
    const submitBtn = document.getElementById("loginSubmitBtn");
    const btnText = document.getElementById("loginBtnText");
    const btnSpinner = document.getElementById("loginBtnSpinner");

    if (loginForm && submitBtn && btnText && btnSpinner) {
        loginForm.addEventListener("submit", function () {
            // We don't preventDefault() here - the form still submits
            // normally to Flask. We're only changing how the button
            // LOOKS while the browser waits for the server's response,
            // so the admin gets instant visual feedback that their
            // click registered instead of wondering if it worked.
            submitBtn.disabled = true;
            btnText.textContent = "Logging in...";
            btnSpinner.classList.remove("d-none");
        });
    }
});
