import asyncio
import hashlib
import os
import uuid

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, status

from app.core import config

_LOCAL_UPLOAD_DIR = "/tmp/ocr_uploads"
LOCAL_BUCKET = "__local__"


def _ext_from_mime(mime_type: str) -> str:
    return {"image/jpeg": "jpg", "image/png": "png", "application/pdf": "pdf"}[mime_type]


class S3Service:
    def __init__(self) -> None:
        self._bucket = config.AWS_S3_BUCKET_NAME
        self._region = config.AWS_REGION

    def _client(self) -> boto3.client:
        return boto3.client(
            "s3",
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            region_name=self._region,
        )

    @staticmethod
    def compute_hash(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    async def upload(
        self,
        content: bytes,
        user_id: int,
        mime_type: str,
        original_filename: str,
    ) -> tuple[str, str]:
        """S3 또는 로컬 스토리지에 파일을 업로드합니다.

        Returns:
            (s3_key, file_hash) — AWS_S3_BUCKET_NAME 미설정 시 로컬 경로 반환
        """
        file_hash = self.compute_hash(content)

        if not self._bucket:
            return await self._upload_local(content, mime_type), file_hash

        s3_key = f"ocr/{user_id}/{uuid.uuid4().hex}.{_ext_from_mime(mime_type)}"

        def _do_upload() -> None:
            self._client().put_object(
                Bucket=self._bucket,
                Key=s3_key,
                Body=content,
                ContentType=mime_type,
                ContentDisposition=f'inline; filename="{original_filename}"',
            )

        try:
            await asyncio.to_thread(_do_upload)
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"S3 업로드에 실패했습니다: {exc}",
            ) from exc

        return s3_key, file_hash

    async def delete(self, s3_key: str) -> None:
        if not self._bucket:
            await asyncio.to_thread(os.remove, s3_key)
            return

        def _do_delete() -> None:
            self._client().delete_object(Bucket=self._bucket, Key=s3_key)

        await asyncio.to_thread(_do_delete)

    @staticmethod
    async def _upload_local(content: bytes, mime_type: str) -> str:
        os.makedirs(_LOCAL_UPLOAD_DIR, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.{_ext_from_mime(mime_type)}"
        local_path = os.path.join(_LOCAL_UPLOAD_DIR, filename)

        def _write() -> None:
            with open(local_path, "wb") as f:
                f.write(content)

        await asyncio.to_thread(_write)
        return local_path
