from datetime import datetime

from sqlalchemy import BigInteger, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models.base import Base


class Guide(Base):
    __tablename__ = "guides"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    guide_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    patient_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guide_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    feedback_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_guides_guide_id", "guide_id"),)
