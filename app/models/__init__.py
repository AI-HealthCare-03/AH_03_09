# Base.metadata에 모든 모델을 등록하기 위한 부수효과 임포트.
# Alembic autogenerate 및 테스트 fixture(create_all)가 모든 테이블을 인식하도록 한다.
from app.models import chat, drug_master, users  # noqa: F401
from app.models.ocr import ocr_document  # noqa: F401
