// trainees.js
// -----------
// Behavior specific to the Add/Edit form and the trainee list page.
// Loaded only on templates under templates/trainees/ (see each
// template's dashboard_extra_scripts block) - dashboard.js still
// handles the shared sidebar/dark-mode/tooltip/toast behavior that
// every dashboard-area page needs, including these.

document.addEventListener("DOMContentLoaded", function () {

    // ----------------------------------------------------------------
    // 1. ADD/EDIT FORM: loading spinner on submit
    // ----------------------------------------------------------------
    // Same pattern as the login page in Milestone 3 (static/js/auth.js)
    // - gives instant feedback that the click registered, which matters
    // extra here since a file upload can take a moment longer than a
    // simple login POST.
    const traineeForm = document.getElementById("traineeForm");
    const submitBtn = document.getElementById("traineeSubmitBtn");
    const submitText = document.getElementById("traineeSubmitText");
    const submitSpinner = document.getElementById("traineeSubmitSpinner");

    if (traineeForm && submitBtn && submitSpinner) {
        traineeForm.addEventListener("submit", function () {
            submitBtn.disabled = true;
            submitSpinner.classList.remove("d-none");
        });
    }

    // ----------------------------------------------------------------
    // 2. DELETE CONFIRMATION MODAL (list.html)
    // ----------------------------------------------------------------
    // There is ONE modal in list.html shared by every row's delete
    // button. Bootstrap fires a "show.bs.modal" event right before the
    // modal opens, and tells us WHICH button triggered it via
    // event.relatedTarget - we read that button's data-trainee-id /
    // data-trainee-name attributes and use them to fill in the modal's
    // text and point its form at the correct delete URL, all just in
    // time before the admin sees it.
    const deleteModal = document.getElementById("deleteModal");
    if (deleteModal) {
        deleteModal.addEventListener("show.bs.modal", function (event) {
            const triggerButton = event.relatedTarget;
            const traineeId = triggerButton.getAttribute("data-trainee-id");
            const traineeName = triggerButton.getAttribute("data-trainee-name");

            const nameSpan = document.getElementById("deleteModalTraineeName");
            const deleteForm = document.getElementById("deleteModalForm");

            if (nameSpan) {
                nameSpan.textContent = traineeName;
            }
            if (deleteForm) {
                // Builds a URL like /trainees/7/delete from the id we
                // just read off the button - matches the Flask route
                // trainees_bp.route("/<int:trainee_id>/delete") exactly.
                deleteForm.action = `/trainees/${traineeId}/delete`;
            }
        });
    }

    // ----------------------------------------------------------------
    // 3. INSTANT CLIENT-SIDE FILTER (current page only)
    // ----------------------------------------------------------------
    // This is a responsiveness NICE-TO-HAVE on top of the real search:
    // as the admin types, rows on the CURRENTLY LOADED page (up to 10,
    // per routes/trainees.py's pagination) are shown/hidden instantly
    // with no network request. Pressing Enter or clicking "Search"
    // still runs the full server-side search across ALL trainees (not
    // just this page) - that's the one that actually matters for
    // correctness on large datasets; this is just instant feedback.
    const searchInput = document.getElementById("searchInput");
    const traineeTable = document.getElementById("traineeTable");

    if (searchInput && traineeTable) {
        searchInput.addEventListener("input", function () {
            const filterText = searchInput.value.trim().toLowerCase();
            const rows = traineeTable.querySelectorAll("tbody tr");

            rows.forEach(function (row) {
                const rowText = row.textContent.toLowerCase();
                row.style.display = rowText.includes(filterText) ? "" : "none";
            });
        });
    }

    // ----------------------------------------------------------------
    // 4. AADHAAR REVEAL TOGGLE (detail.html)
    // ----------------------------------------------------------------
    // VERSION 1.0: the trainee detail page shows a MASKED Aadhaar
    // number by default ("XXXX XXXX 9012" - see
    // models/trainee.py -> masked_aadhaar and utils/security.py). The
    // full number is already present in the rendered HTML (there's no
    // extra network request involved in "revealing" it - the page is
    // only visible to a logged-in admin anyway, same as every other
    // trainee field), we simply toggle which of the two spans is shown.
    const aadhaarRevealBtn = document.getElementById("aadhaarRevealBtn");
    const aadhaarMasked = document.getElementById("aadhaarMasked");
    const aadhaarFull = document.getElementById("aadhaarFull");
    const aadhaarRevealIcon = document.getElementById("aadhaarRevealIcon");

    if (aadhaarRevealBtn && aadhaarMasked && aadhaarFull) {
        aadhaarRevealBtn.addEventListener("click", function () {
            const isRevealed = !aadhaarFull.classList.contains("d-none");
            aadhaarFull.classList.toggle("d-none", isRevealed);
            aadhaarMasked.classList.toggle("d-none", !isRevealed);
            if (aadhaarRevealIcon) {
                aadhaarRevealIcon.classList.toggle("bi-eye", isRevealed);
                aadhaarRevealIcon.classList.toggle("bi-eye-slash", !isRevealed);
            }
        });
    }
});
