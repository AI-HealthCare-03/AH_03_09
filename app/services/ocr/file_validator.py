from fastapi import HTTPException, UploadFile, status

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_FILES = 5

# MIME 타입별 허용 확장자 (REQ-OCR-002 이중 검증)
_MIME_TO_EXTENSIONS: dict[str, set[str]] = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "application/pdf": {".pdf"},
}


async def validate_upload(file: UploadFile) -> bytes:
    """MIME + 확장자 이중 검증, 크기 검사 후 raw bytes 반환. (REQ-OCR-002)"""
    if not file.content_type or file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="지원하지 않는 파일 형식입니다. JPEG·PNG·PDF만 허용됩니다.",
        )

    filename = file.filename or ""
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext not in _MIME_TO_EXTENSIONS.get(file.content_type, set()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"확장자({ext})가 파일 형식({file.content_type})과 일치하지 않습니다.",
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


def validate_file_count(files: list[UploadFile]) -> None:
    """최대 파일 수 초과 검사. (REQ-OCR-002)"""
    if len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="업로드할 파일을 선택해주세요.",
        )
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"한 번에 최대 {MAX_FILES}개 파일까지 업로드할 수 있습니다.",
        )
