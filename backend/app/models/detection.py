"""Detection model — a single detected road damage instance."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReviewStatus(str, enum.Enum):
    UNREVIEWED = "unreviewed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"
    PUBLISHED = "published"


class Detection(Base):
    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    detection_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    inspection_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("inspection_runs.id"), nullable=False
    )
    image_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("images.id"), nullable=False
    )
    damage_type: Mapped[str] = mapped_column(String(100), nullable=False)
    class_id: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    # Bounding box (pixel coordinates)
    x_min: Mapped[float] = mapped_column(Float, nullable=False)
    y_min: Mapped[float] = mapped_column(Float, nullable=False)
    x_max: Mapped[float] = mapped_column(Float, nullable=False)
    y_max: Mapped[float] = mapped_column(Float, nullable=False)
    center_x: Mapped[float] = mapped_column(Float, nullable=False)
    center_y: Mapped[float] = mapped_column(Float, nullable=False)
    # Geographic location (inherited from source image)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_method: Mapped[str] = mapped_column(
        String(50), default="camera_exif_approximation", nullable=False
    )
    # Review
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.UNREVIEWED, nullable=False
    )
    review_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Model tracking
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # ArcGIS
    arcgis_object_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    inspection_run = relationship("InspectionRun", back_populates="detections")
    image = relationship("Image", back_populates="detections")
    review_actions = relationship("ReviewAction", back_populates="detection", cascade="all, delete-orphan")
