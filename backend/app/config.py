"""Application configuration loaded from environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./georoad.db"

    # File storage
    upload_dir: Path = Path("./uploads")
    max_upload_size_mb: int = 50
    allowed_extensions: str = ".jpg,.jpeg,.png"

    # YOLO Model
    model_weights_path: Path = Path("./models/road_damage_best.pt")
    default_confidence_threshold: float = 0.25
    default_iou_threshold: float = 0.45

    # ArcGIS Online
    arcgis_portal_url: str = ""
    arcgis_client_id: str = ""
    arcgis_client_secret: str = ""
    arcgis_feature_layer_url: str = ""
    arcgis_web_map_url: str = ""

    # App
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def allowed_extensions_set(self) -> set[str]:
        return {ext.strip().lower() for ext in self.allowed_extensions.split(",")}

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def arcgis_enabled(self) -> bool:
        return bool(self.arcgis_portal_url and self.arcgis_client_id)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
