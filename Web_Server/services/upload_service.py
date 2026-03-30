import mimetypes
from app.storage import supabase


def upload_file(bucket: str, file_bytes: bytes, filename: str, user_id: int):

    filename = filename.replace(" ", "_")

    storage_path = f"user_{user_id}/{filename}"

    content_type, _ = mimetypes.guess_type(filename)

    supabase.storage.from_(bucket).upload(
        storage_path,
        file_bytes,
        {
            "content-type": content_type or "application/octet-stream",
            "upsert": "true"
        }
    )

    url = supabase.storage.from_(bucket).get_public_url(storage_path)

    return url