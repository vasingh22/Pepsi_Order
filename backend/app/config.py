from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Set, Union

from pydantic import BaseModel, Field, ConfigDict, field_validator


class Settings(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    app_name: str = "Invoice OCR Service"
    sample_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "PickSample200",
        description="Directory containing reference/sample PDF invoices.",
    )
    temp_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / ".tmp",
        description="Directory for temporary storage of uploaded files.",
    )
    default_languages: List[str] = Field(
        default_factory=lambda: ["en"],
        description="Default languages passed to Surya OCR.",
    )
    allowed_extensions: Set[str] = Field(
        default_factory=lambda: {"pdf"},
        description="File extensions permitted for upload/extraction.",
    )
    max_upload_size_mb: int = Field(
        default=25,
        ge=1,
        description="Maximum upload size in megabytes for invoice PDFs.",
    )
    vendor_master_path: Optional[Path] = Field(
        default=None,
        description="Optional path to a JSON file containing vendor aliases.",
    )
    sku_master_path: Optional[Path] = Field(
        default=None,
        description="Optional path to a JSON file containing SKU aliases.",
    )
    uom_master_path: Optional[Path] = Field(
        default=None,
        description="Optional path to a JSON file containing UOM aliases.",
    )

    @field_validator(
        "sample_dir",
        "temp_dir",
        "vendor_master_path",
        "sku_master_path",
        "uom_master_path",
        mode="before",
    )
    @classmethod
    def _expand_path(cls, value: Union[str, Path, None]) -> Optional[Path]:
        if value is None or value == "":
            return None
        path = Path(value).expanduser()
        return path


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    return settings

