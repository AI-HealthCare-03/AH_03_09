import asyncio
import hashlib
import uuid

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, status

from app.core import config


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
        user_id: uuid.UUID,
        mime_type: str,
        original_filename: str,
    ) -> tuple[str, str]:
        """S3에 파일을 업로드합니다.

        Returns:
            (s3_key, file_hash)
        """
        file_hash = self.compute_hash(content)
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
        def _do_delete() -> None:
            self._client().delete_object(Bucket=self._bucket, Key=s3_key)

        await asyncio.to_thread(_do_delete)
