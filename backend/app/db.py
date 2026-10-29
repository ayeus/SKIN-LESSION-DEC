import os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, String, Text, DateTime, JSON, Integer, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

ROOT = Path(os.environ.get("DERMA_STORAGE", "data")).resolve()
ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
engine = create_engine(
    os.environ.get("DATABASE_URL", f"sqlite:///{ROOT / 'research.db'}")
)
Session = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Dataset(Base):
    __tablename__ = "datasets"
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    modality: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(Text)
    license: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(Text)
    profile: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Run(Base):
    __tablename__ = "runs"
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(50))
    dataset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Audit(Base):
    __tablename__ = "audit_events"
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    action: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AccessSession(Base):
    __tablename__ = "access_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    expires_at: Mapped[int] = mapped_column(Integer)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class LoginThrottle(Base):
    __tablename__ = "login_throttles"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[int] = mapped_column(Integer)
    blocked_until: Mapped[int] = mapped_column(Integer, default=0)


class DatasetGrant(Base):
    __tablename__ = "dataset_grants"
    dataset_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
