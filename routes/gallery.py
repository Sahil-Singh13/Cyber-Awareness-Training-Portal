import os

from flask import Blueprint, abort, flash, redirect, render_template, send_from_directory, url_for
from flask_login import login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileSize, MultipleFileField
from wtforms import SubmitField
from wtforms.validators import Optional

from config import Config
from models import db
from models.activity_log import ActivityLog
from models.gallery_photo import GalleryPhoto
from utils.file_helpers import delete_file_if_exists, save_uploaded_file

gallery_bp = Blueprint("gallery", __name__, url_prefix="/gallery")


class GalleryUploadForm(FlaskForm):
    images = MultipleFileField(
        "Group Training Images",
        validators=[
            Optional(),
            FileAllowed(["jpg", "jpeg", "png"], message="Only JPG, JPEG, or PNG files are allowed."),
            FileSize(max_size=Config.MAX_CONTENT_LENGTH, message="Each file must be 5 MB or smaller."),
        ],
    )
    submit = SubmitField("Upload Images")


@gallery_bp.route("/", methods=["GET", "POST"])
@login_required
def gallery_home():
    form = GalleryUploadForm()
    if form.validate_on_submit():
        uploaded_count = 0
        try:
            for image in form.images.data or []:
                filename = save_uploaded_file(
                    image, Config.GALLERY_FOLDER, Config.ALLOWED_GALLERY_EXTENSIONS
                )
                if filename:
                    db.session.add(GalleryPhoto(filename=filename))
                    uploaded_count += 1
            if not uploaded_count:
                flash("Choose at least one image to upload.", "warning")
            else:
                db.session.commit()
                ActivityLog.log("gallery_images_uploaded", f"Uploaded {uploaded_count} gallery image(s).")
                flash(f"{uploaded_count} image(s) uploaded successfully.", "success")
                return redirect(url_for("gallery.gallery_home"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
        except Exception:
            db.session.rollback()
            flash("Unable to upload the images. Please try again.", "danger")

    images = GalleryPhoto.query.order_by(GalleryPhoto.created_at.desc()).all()
    return render_template("gallery/index.html", form=form, images=images, active_page="gallery")


@gallery_bp.route("/images/<path:filename>")
@login_required
def view_image(filename):
    if not os.path.exists(os.path.join(Config.GALLERY_FOLDER, filename)):
        abort(404)
    return send_from_directory(Config.GALLERY_FOLDER, filename)


@gallery_bp.route("/<int:image_id>/delete", methods=["POST"])
@login_required
def delete_image(image_id):
    image = GalleryPhoto.query.get_or_404(image_id)
    try:
        delete_file_if_exists(Config.GALLERY_FOLDER, image.filename)
        db.session.delete(image)
        db.session.commit()
        ActivityLog.log("gallery_image_deleted", "Deleted a gallery image.")
        flash("Image deleted successfully.", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to delete the image. Please try again.", "danger")
    return redirect(url_for("gallery.gallery_home"))
