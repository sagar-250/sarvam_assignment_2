from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Memory(Base):
    __tablename__ = "memory"
    __table_args__ = (
        UniqueConstraint("observed_form", "canonical_form", name="ux_memory_observed_canonical"),
        Index("ix_memory_observed_form", "observed_form"),
        Index("ix_memory_active", "active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    observed_form: Mapped[str] = mapped_column(String, nullable=False)
    canonical_form: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False, default="other")
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    evidence: Mapped[list["Evidence"]] = relationship(
        "Evidence", back_populates="memory", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "observed_form": self.observed_form,
            "canonical_form": self.canonical_form,
            "entity_type": self.entity_type,
            "token_count": self.token_count,
            "evidence_count": self.evidence_count,
            "confidence": round(self.confidence, 3),
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (Index("ix_evidence_memory_id", "memory_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    memory_id: Mapped[int | None] = mapped_column(
        ForeignKey("memory.id", ondelete="CASCADE"), nullable=True
    )
    observed_form: Mapped[str] = mapped_column(String, nullable=False)
    canonical_form: Mapped[str] = mapped_column(String, nullable=False)
    source_asr: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_corrected: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False, default="observed_pair")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    memory: Mapped["Memory"] = relationship("Memory", back_populates="evidence")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "memory_id": self.memory_id,
            "observed_form": self.observed_form,
            "canonical_form": self.canonical_form,
            "source_asr": self.source_asr,
            "source_corrected": self.source_corrected,
            "source_type": self.source_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
