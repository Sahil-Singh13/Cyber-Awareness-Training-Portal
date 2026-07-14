"""
utils/file_helpers.py
----------------------
Shared helper functions for handling certificate uploads. Used by
routes/trainees.py for both the Add and Edit trainee forms.

WHY THESE LIVE IN utils/ AND NOT INSIDE routes/trainees.py DIRECTLY
------------------------------------------------------------------------
Add and Edit both need to "save an uploaded file safely" and "delete an
old file when it's replaced/removed" - identical logic in two places.
Pulling it out here means we write it once, test it once, and both
routes call the same trusted function - the DRY principle again, same
reasoning as the template partials in Milestone 4.
"""

import os
import uuid
from werkzeug.utils import secure_filename


def allowed_extension(filename, allowed_extensions):
    """
    Checks whether `filename` ends in one of `allowed_extensions`
    (e.g. {"pdf"} or {"jpg", "jpeg", "png"}).

    "document.PDF".rsplit(".", 1) -> ["document", "PDF"] - we lowercase the
    extension before comparing so "PNG", "Png", and "png" are all
    treated the same way.
    """
    if "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in allowed_extensions


def generate_unique_filename(original_filename):
    """
    Builds a filename that can NEVER collide with another trainee's
    upload, even if two people happen to upload files both named
    "certificate.pdf".

    HOW:
    1. secure_filename() (from Werkzeug) strips anything dangerous from
       the ORIGINAL name - path separators, "..", null bytes, etc. -
       so a malicious filename can't be used to write outside our
       uploads/ folder (a real security concern called "path
       traversal").
    2. We keep the cleaned-up extension (.pdf, .jpg, ...) but throw away
       the rest of the original name entirely, replacing it with a
       uuid4() - a 32-character random identifier where the odds of two
       calls ever producing the same value are astronomically small.

    Example: "My Certificate (Final).PDF" -> "9f86d081-...-a3e2.pdf"
    """
    safe_original = secure_filename(original_filename)
    extension = safe_original.rsplit(".", 1)[1].lower() if "." in safe_original else ""
    unique_name = f"{uuid.uuid4().hex}.{extension}" if extension else uuid.uuid4().hex
    return unique_name


def save_uploaded_file(file_storage, destination_folder, allowed_extensions):
    """
    Validates and saves ONE uploaded file (a Werkzeug FileStorage
    object, e.g. form.certificate.data).

    Returns the new unique filename on success, or None if there was no
    file to save (this is normal - certificates are optional on
    Add, and the admin might not choose to replace them on Edit).

    Raises ValueError with a human-readable message if the file exists
    but fails validation (wrong extension) - the calling route catches
    this and flashes it to the admin instead of letting it crash the
    request.
    """
    if not file_storage or file_storage.filename == "":
        return None

    if not allowed_extension(file_storage.filename, allowed_extensions):
        allowed_list = ", ".join(sorted(allowed_extensions)).upper()
        raise ValueError(f"Invalid file type. Allowed: {allowed_list}")

    # Make sure the destination folder physically exists before we try
    # to write into it - protects against the "Missing Upload Folder"
    # error case the assignment specifically calls out.
    os.makedirs(destination_folder, exist_ok=True)

    new_filename = generate_unique_filename(file_storage.filename)
    full_path = os.path.join(destination_folder, new_filename)
    file_storage.save(full_path)
    return new_filename


def delete_file_if_exists(folder, filename):
    """
    Removes a previously-uploaded file from disk, used when:
      - an admin deletes a trainee (clean up their certificate)
      - an admin replaces a certificate during Edit (remove the
        old file so we don't silently accumulate orphaned files forever)

    Deliberately silent/safe if the file is already missing (filename
    is None, or the file was somehow already deleted) - "delete
    something that isn't there" should never crash the request; it
    just means there's nothing left to do.
    """
    if not filename:
        return
    full_path = os.path.join(folder, filename)
    if os.path.exists(full_path):
        os.remove(full_path)
