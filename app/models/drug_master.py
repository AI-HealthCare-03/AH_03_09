from sqlalchemy import BigInteger, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DrugMaster(Base):
    __tablename__ = "drug_master"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    __table_args__ = (
        Index(
            "ix_drug_master_item_name_trgm",
            "item_name",
            postgresql_using="gin",
            postgresql_ops={"item_name": "gin_trgm_ops"},
        ),
    )
