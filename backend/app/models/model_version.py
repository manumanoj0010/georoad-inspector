"""ModelVersion — tracks registered YOLO model configurations."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    weight_path: Mapped[str] = mapped_column(String(500), nullable=False)
    class_mapping: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.25)
    iou_threshold: Mapped[float] = mapped_column(Float, default=0.45)
    evaluation_metrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
