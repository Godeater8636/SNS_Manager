"""
Storage service — ローカルファイルシステム or AWS S3 を透過的に扱う。

環境変数 AWS_ACCESS_KEY_ID が未設定の場合はローカルストレージを使用。
"""

import os
import uuid
import aiofiles
from pathlib import Path
from fastapi import UploadFile
from app.config import settings

# ローカルストレージの絶対パス
_LOCAL_STORAGE_PATH = Path(getattr(settings, "LOCAL_STORAGE_PATH", "./media")).resolve()


def _is_s3_configured() -> bool:
    return bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_S3_BUCKET)


async def upload_file(file: UploadFile, prefix: str = "uploads") -> str:
    """
    ファイルをアップロードし、アクセス可能な URL を返す。

    S3 が設定されている場合は S3 にアップロード。
    未設定の場合はローカルの media/ ディレクトリに保存し、
    API サーバー経由でアクセス可能な URL を返す。
    """
    ext = Path(file.filename or "file").suffix
    filename = f"{prefix}/{uuid.uuid4().hex}{ext}"

    if _is_s3_configured():
        return await _upload_to_s3(file, filename)
    else:
        return await _upload_to_local(file, filename)


async def _upload_to_s3(file: UploadFile, key: str) -> str:
    import boto3
    from botocore.exceptions import ClientError

    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    content = await file.read()
    s3.put_object(
        Bucket=settings.AWS_S3_BUCKET,
        Key=key,
        Body=content,
        ContentType=file.content_type or "application/octet-stream",
    )
    return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"


async def _upload_to_local(file: UploadFile, relative_path: str) -> str:
    dest = _LOCAL_STORAGE_PATH / relative_path
    dest.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    async with aiofiles.open(dest, "wb") as f:
        await f.write(content)

    # FastAPI のメディアルート経由でアクセス
    return f"{settings.APP_BASE_URL}/media/{relative_path}"
