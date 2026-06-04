from sqlalchemy import BigInteger, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DrugMaster(Base):
    __tablename__ = "drug_master"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    dosage: Mapped[str | None] = mapped_column(Text, nullable=True)
    cautions: Mapped[str | None] = mapped_column(Text, nullable=True)
    side_effects: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage: Mapped[str | None] = mapped_column(Text, nullable=True)
    etc_otc_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        Index(
            "ix_drug_master_item_name_trgm",
            "item_name",
            postgresql_using="gin",
            postgresql_ops={"item_name": "gin_trgm_ops"},
        ),
    )
