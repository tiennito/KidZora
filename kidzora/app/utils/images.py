"""
app/utils/images.py
───────────────────
Centralised image optimisation + Supabase Storage upload helper.

Usage (images):
    from app.utils.images import upload_to_storage, is_image_ext

    public_url = upload_to_storage(
        file_storage,        # werkzeug FileStorage object
        bucket,              # Supabase Storage bucket name  e.g. 'product-images'
        storage_path,        # path inside the bucket        e.g. 'sellers/123/abc.webp'
        max_width=900,
        max_height=900,
        quality=82,
    )

Usage (non-image / video):
    public_url = upload_raw_to_storage(file_storage, bucket, storage_path)

All images are:
  1. EXIF auto-rotated (phone photos stay upright)
  2. Downscaled proportionally if larger than max_w / max_h (never upscaled)
  3. Re-encoded as WebP (better compression, wide browser support)
  4. Uploaded to the specified Supabase Storage bucket

Non-image files (video, PDF…) are uploaded as-is via upload_raw_to_storage().

Buckets required in Supabase (see Database_Setup_Step27_Storage_Buckets.sql):
  - product-images   (public)
  - avatars          (public)
  - return-evidence  (public)
  - review-media     (public)
"""

import io

try:
    from PIL import Image, ImageOps
    _PILLOW_AVAILABLE = True
except ImportError:
    _PILLOW_AVAILABLE = False

IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff'}

_MIME_MAP = {
    'jpg': 'image/jpeg',  'jpeg': 'image/jpeg',
    'png': 'image/png',   'gif': 'image/gif',
    'webp': 'image/webp', 'bmp': 'image/bmp',
    'tiff': 'image/tiff',
    'mp4': 'video/mp4',   'mov': 'video/quicktime',
    'avi': 'video/x-msvideo', 'webm': 'video/webm',
    'mkv': 'video/x-matroska',
    'pdf': 'application/pdf',
}


def is_image_ext(filename: str) -> bool:
    """Return True if the filename's extension is a recognised image type."""
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in IMAGE_EXTENSIONS


def _optimise_to_bytes(file_storage, max_width: int, max_height: int,
                       quality: int = 82) -> tuple:
    """
    Read and optimise the image; return (data_bytes, content_type_str).
    Falls back to raw bytes if Pillow is unavailable or the file is invalid.
    """
    raw = file_storage.read()
    orig_ext = (file_storage.filename.rsplit('.', 1)[1].lower()
                if '.' in file_storage.filename else 'jpg')

    if not _PILLOW_AVAILABLE:
        return raw, _MIME_MAP.get(orig_ext, 'image/jpeg')

    try:
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)           # auto-rotate from EXIF
        img.thumbnail((max_width, max_height), Image.LANCZOS)  # never upscales

        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGBA', img.size, (255, 255, 255, 255))
            try:
                background.paste(img, mask=img.split()[-1])
            except Exception:
                background.paste(img)
            img = background

        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')

        buf = io.BytesIO()
        img.save(buf, format='WEBP', quality=quality, method=4)
        return buf.getvalue(), 'image/webp'

    except Exception as exc:
        print(f'[images] optimise failed, uploading raw: {exc}')
        return raw, _MIME_MAP.get(orig_ext, 'image/jpeg')


def upload_to_storage(file_storage, bucket: str, storage_path: str,
                      max_width: int, max_height: int,
                      quality: int = 82) -> str:
    """
    Optimise an image and upload it to Supabase Storage.

    *storage_path* is the path inside the bucket (no leading slash).
    The extension is forced to ``.webp`` when optimisation succeeds.

    Returns the public URL string.
    Raises RuntimeError if the upload fails.
    """
    from app.extensions import supabase_admin

    data, content_type = _optimise_to_bytes(file_storage, max_width, max_height, quality)

    # Ensure the path ends with .webp when we produced a WebP file
    if content_type == 'image/webp' and not storage_path.lower().endswith('.webp'):
        base = storage_path.rsplit('.', 1)[0] if '.' in storage_path.split('/')[-1] else storage_path
        storage_path = base + '.webp'

    try:
        supabase_admin.storage.from_(bucket).upload(
            path=storage_path,
            file=data,
            file_options={"content-type": content_type, "upsert": "true"},
        )
    except Exception as exc:
        raise RuntimeError(
            f'Supabase Storage upload failed [{bucket}/{storage_path}]: {exc}'
        ) from exc

    return supabase_admin.storage.from_(bucket).get_public_url(storage_path)


def upload_raw_to_storage(file_storage, bucket: str, storage_path: str) -> str:
    """
    Upload a non-image file (video, PDF…) to Supabase Storage as-is.

    Returns the public URL string.
    Raises RuntimeError if the upload fails.
    """
    from app.extensions import supabase_admin

    data = file_storage.read()
    orig_ext = (file_storage.filename.rsplit('.', 1)[1].lower()
                if '.' in file_storage.filename else 'bin')
    content_type = _MIME_MAP.get(orig_ext, 'application/octet-stream')

    try:
        supabase_admin.storage.from_(bucket).upload(
            path=storage_path,
            file=data,
            file_options={"content-type": content_type, "upsert": "true"},
        )
    except Exception as exc:
        raise RuntimeError(
            f'Supabase Storage upload failed [{bucket}/{storage_path}]: {exc}'
        ) from exc

    return supabase_admin.storage.from_(bucket).get_public_url(storage_path)
