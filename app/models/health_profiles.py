from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models.base import Base


class GenderType(StrEnum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "OTHER"


class ExerciseHabit(StrEnum):
    REGULAR = "REGULAR"
    IRREGULAR = "IRREGULAR"
    NONE = "NONE"


class AlcoholHabit(StrEnum):
    NONE = "NONE"
    MODERATE = "MODERATE"
    HEAVY = "HEAVY"


class ProfileChangedBy(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    ADMIN = "ADMIN"


class HealthProfile(Base):
    __tablename__ = "health_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    age_range: Mapped[str | None] = mapped_column(String(20), nullable=True)
    height_cm: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    weight_kg: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    blood_pressure_systolic: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    blood_pressure_diastolic: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    primary_conditions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    allergies: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    current_medications: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    lifestyle_exercise: Mapped[str] = mapped_column(String(20), nullable=False, default=ExerciseHabit.NONE)
    lifestyle_smoking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lifestyle_alcohol: Mapped[str] = mapped_column(String(20), nullable=False, default=AlcoholHabit.NONE)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class HealthProfileHistory(Base):
    __tablename__ = "health_profile_histories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    health_profile_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("health_profiles.id", ondelete="CASCADE"), nullable=False
    )
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    changed_by: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
