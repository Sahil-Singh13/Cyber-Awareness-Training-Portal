// reports_settings.js
// --------------------
// Loading-spinner behavior for the Import form on the Reports page.
// Same pattern as auth.js (Milestone 3) and trainees.js (Milestone 5) -
// disable the button and show a spinner the instant it's clicked, since
// parsing a large Excel file can take a moment.

document.addEventListener("DOMContentLoaded", function () {
    const importForm = document.getElementById("importForm");
    const importBtn = document.getElementById("importSubmitBtn");
    const importSpinner = document.getElementById("importSubmitSpinner");

    if (importForm && importBtn && importSpinner) {
        importForm.addEventListener("submit", function () {
            importBtn.disabled = true;
            importSpinner.classList.remove("d-none");
        });
    }
});
