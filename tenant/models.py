import datetime
from datetime import datetime, timezone
from typing import Any, List

from passlib.context import CryptContext
from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from core.settings import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class Base(AsyncAttrs, DeclarativeBase):
    pass


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

    role: Mapped[List["Role"]] = relationship(
        "Role", back_populates="organisation", cascade="all, delete"
    )

    member: Mapped[List["Member"]] = relationship(
        "Member", back_populates="organisation", cascade="all, delete"
    )


class User(BaseModel):
    __tablename__ = "user"

    email: Mapped[str] = mapped_column(String(length=100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    profile: Mapped[JSON] = mapped_column(JSON, nullable=False, default={})

    member: Mapped[List["Member"]] = relationship(
        "Member", back_populates="user", cascade="all, delete"
    )


class Role(Base):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(length=50), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    org_id: Mapped[BigInteger] = mapped_column(
        ForeignKey("organisation.id", ondelete="CASCADE"), nullable=False
    )
    organisation: Mapped[Organisation] = relationship(
        "Organisation", back_populates="role", single_parent=True, uselist=False
    )

    member: Mapped[List["Member"]] = relationship(
        "Member", back_populates="role", cascade="all, delete"
    )


class Member(BaseModel):
    __tablename__ = "member"

    org_id: Mapped[BigInteger] = mapped_column(
        ForeignKey("organisation.id", ondelete="CASCADE"), nullable=False
    )
    organisation: Mapped[Organisation] = relationship(
        "Organisation", back_populates="role", single_parent=True, uselist=False
    )

    user_id: Mapped[BigInteger] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped[User] = relationship(
        "User", back_populates="member", single_parent=True, uselist=False
    )

    role_id: Mapped[BigInteger] = mapped_column(
        ForeignKey("role.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[Role] = relationship(
        "Role", back_populates="member", single_parent=True, uselist=False
    )
