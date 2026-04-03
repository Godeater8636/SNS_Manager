"""
メディアアップロードエンドポイント。

S3 が設定されている場合は S3 にアップロード。
未設定の場合はローカルの media/ ディレクトリに保存し、
/media/{path} で配信する。
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.services.storage_service import upload_file

router = APIRouter(prefix="/media", tags=["media"])

ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "video/mp4", "video/quicktime",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[dict]:
    """
    メディアファイルをアップロードし、URL を返す。

    - 画像: JPEG / PNG / GIF / WebP（最大 50 MB）
    - 動画: MP4 / MOV（最大 50 MB）

    レスポンスの `file_url` を投稿作成時の `media_urls` に含めてください。
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail={
                "code": "UNSUPPORTED_MEDIA_TYPE",
                "message": f"対応フォーマット: {', '.join(ALLOWED_CONTENT_TYPES)}",
            },
        )

    # ファイルサイズチェック（先頭 MAX+1 バイト読み取り）
    chunk = await file.read(MAX_FILE_SIZE + 1)
    if len(chunk) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail={"code": "FILE_TOO_LARGE", "message": "ファイルサイズは 50 MB 以下にしてください"},
        )

    # ファイルポインタを先頭に戻す
    import io
    file.file = io.BytesIO(chunk)

    file_url = await upload_file(file, prefix=f"users/{current_user.id}")

    return SuccessResponse(data={"file_url": file_url, "content_type": file.content_type})
