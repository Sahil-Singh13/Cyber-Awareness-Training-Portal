import io

from models.gallery_photo import GalleryPhoto


def test_gallery_requires_login(client):
    response = client.get("/gallery/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_gallery_upload_and_delete(logged_in_client, app):
    response = logged_in_client.post(
        "/gallery/",
        data={"images": (io.BytesIO(b"image data"), "group.jpg")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        image = GalleryPhoto.query.one()
        image_id = image.id

    response = logged_in_client.post(f"/gallery/{image_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert GalleryPhoto.query.get(image_id) is None
