"""ArcGISPublication — tracks publishing events to ArcGIS Online."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PublicationStatus(str, enum.Enum):
    PENDING = "pending"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class ArcGISPublication(Base):
    __tablename__ = "arcgis_publications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("inspection_runs.id"), nullable=False
    )
    feature_layer_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    published_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus), default=PublicationStatus.PENDING, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    inspection_run = relationship("InspectionRun", back_populates="publications")
