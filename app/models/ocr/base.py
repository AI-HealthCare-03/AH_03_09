from sqlalchemy import BigInteger, Column, Table
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Tortoise ORM이 관리하는 users 테이블의 stub 정의.
# SQLAlchemy가 ocr_documents.user_id FK를 resolve하는 데에만 사용됨.
# create_all()은 테이블 존재 여부를 먼저 확인하므로 실제 생성은 일어나지 않음.
Table("users", Base.metadata, Column("id", BigInteger, primary_key=True), extend_existing=True)
