import uuid
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from backend.core.config import settings

_client: Minio | None = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        _ensure_bucket(_client)
    return _client


def _ensure_bucket(client: Minio) -> None:
    try:
        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)
    except S3Error as e:
        raise RuntimeError(f"MinIO bucket setup failed: {e}") from e


def generate_presigned_put_url(
    entity_type: str,
    entity_id: str,
    doc_type: str,
    file_name: str,
    expires: int = 3600,
) -> tuple[str, str]:
    """
    Returns (presigned_put_url, object_key).
    The client uploads directly to MinIO using this URL.
    """
    client = get_minio_client()
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "bin"
    object_key = f"{entity_type}/{entity_id}/{doc_type}/{uuid.uuid4()}.{ext}"

    url = client.presigned_put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_key,
        expires=timedelta(seconds=expires),
    )
    return url, object_key


def get_public_file_url(object_key: str) -> str:
    return f"{settings.MINIO_PUBLIC_URL}/{settings.MINIO_BUCKET}/{object_key}"


def delete_object(object_key: str) -> None:
    client = get_minio_client()
    try:
        client.remove_object(settings.MINIO_BUCKET, object_key)
    except S3Error:
        pass
