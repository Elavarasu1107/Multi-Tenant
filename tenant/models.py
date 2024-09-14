import datetime
from datetime import datetime, timezone
from typing import Any, List

from passlib.context import CryptContext
from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from core.db_manager import DatabaseManager
from core.settings import settings


async def get_db_session():
    try:
        db_manager = DatabaseManager(settings.DB_URL)
        yield db_manager
    finally:
        await db_manager.session.close()
        await db_manager.db.close()


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class Base(AsyncAttrs, DeclarativeBase):

    @property
    def to_dict(self):
        return {
            col.name: getattr(self, col.name)
            for col in self.__table__.columns
            if not col.name == "password"
        }


class BaseModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    settings: Mapped[JSON] = mapped_column(JSON, nullable=False, default={})
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )


class Organisation(BaseModel):
    __tablename__ = "organisation"

    name: Mapped[str] = mapped_column(String(length=50), index=True, nullable=False)
    personal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)

    roles: Mapped[List["Role"]] = relationship(
        "Role", back_populates="organisation", cascade="all, delete"
    )

    members: Mapped[List["Member"]] = relationship(
        "Member", back_populates="organisation", cascade="all, delete"
    )


class User(BaseModel):
    __tablename__ = "user"

    email: Mapped[str] = mapped_column(String(length=100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    profile: Mapped[JSON] = mapped_column(JSON, nullable=False, default={})

    members: Mapped[List["Member"]] = relationship(
        "Member", back_populates="user", cascade="all, delete"
    )

    def __init__(self, **kw: Any):
        self.password = self.set_password(kw.pop("password"))
        super().__init__(**kw)

    def set_password(self, raw_password):
        return pwd_context.hash(raw_password)

    def verify_password(self, raw_password):
        return pwd_context.verify(raw_password, self.password)


class Role(Base):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(length=50), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    org_id: Mapped[BigInteger] = mapped_column(
        ForeignKey("organisation.id", ondelete="CASCADE"), nullable=False
    )
    organisation: Mapped[Organisation] = relationship(
        "Organisation", back_populates="roles", single_parent=True, uselist=False
    )

    members: Mapped[List["Member"]] = relationship(
        "Member", back_populates="roles", cascade="all, delete"
    )


class Member(BaseModel):
    __tablename__ = "member"

    org_id: Mapped[BigInteger] = mapped_column(
        ForeignKey("organisation.id", ondelete="CASCADE"), nullable=False
    )
    organisation: Mapped[Organisation] = relationship(
        "Organisation", back_populates="members", single_parent=True, uselist=False
    )

    user_id: Mapped[BigInteger] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped[User] = relationship(
        "User", back_populates="members", single_parent=True, uselist=False
    )

    role_id: Mapped[BigInteger] = mapped_column(
        ForeignKey("role.id", ondelete="CASCADE"), nullable=False
    )
    roles: Mapped[Role] = relationship(
        "Role", back_populates="members", single_parent=True, uselist=False
    )
