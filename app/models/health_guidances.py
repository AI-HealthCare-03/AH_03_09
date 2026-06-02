from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models.base import Base


class GuidanceType(StrEnum):
    MEDICATION_GUIDE = "MEDICATION_GUIDE"
    LIFESTYLE_GUIDE = "LIFESTYLE_GUIDE"
    DIETARY_GUIDE = "DIETARY_GUIDE"


class VerificationStatus(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FLAGGED = "FLAGGED"


class HealthGuidance(Base):
    __tablename__ = "health_guidances"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    health_profile_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("health_profiles.id", ondelete="SET NULL"), nullable=True
    )
    guidance_type: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    requires_expert_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, default=VerificationStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
