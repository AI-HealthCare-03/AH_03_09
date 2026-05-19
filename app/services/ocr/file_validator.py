from fastapi import HTTPException, UploadFile, status

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


async def validate_upload(file: UploadFile) -> bytes:
    """파일 형식·크기 검사 후 raw bytes 반환. (REQ-OCR-002)"""
    if not file.content_type or file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="지원하지 않는 파일 형식입니다. JPEG·PNG·PDF만 허용됩니다.",
        )

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="빈 파일은 업로드할 수 없습니다.",
        )

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="파일 크기가 10MB를 초과합니다.",
        )

    return content
