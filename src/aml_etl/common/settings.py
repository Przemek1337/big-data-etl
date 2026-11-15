from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from aml_etl.common.dataset_variants import DatasetVariant

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def _default_variants() -> list[DatasetVariant]:
    return [DatasetVariant("HI-Medium"), DatasetVariant("LI-Medium")]


class AmlSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    log_level: str = "INFO"
    local_mongo_uri: str = "mongodb://localhost:27018"
    local_database: str = "aml"
    atlas_uri: str = "mongodb://localhost:27018"
    atlas_database: str = "aml_results"
    mongo_timeout_ms: int = Field(default=10_000, gt=0)
    dataset_variants: Annotated[list[DatasetVariant], NoDecode] = _default_variants()
    data_dir: Path = Path("data")
    kaggle_dataset: str = "ealtman2019/ibm-transactions-for-anti-money-laundering-aml"
    csv_batch_rows: int = Field(default=250_000, gt=0)

    @field_validator("dataset_variants", mode="before")
    @classmethod
    def _split_variants(cls, value: object) -> object:
        if isinstance(value, str):
            names = [name.strip() for name in value.split(",") if name.strip()]
            return [DatasetVariant(name) for name in names]
        return value

    @field_validator("dataset_variants", mode="after")
    @classmethod
    def _require_variants(cls, value: list[DatasetVariant]) -> list[DatasetVariant]:
        if not value:
            raise ValueError("DATASET_VARIANTS must name at least one variant, e.g. HI-Small")
        return value

    @field_validator("log_level", mode="after")
    @classmethod
    def _known_log_level(cls, value: str) -> str:
        level = value.strip().upper()
        if level not in LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(LOG_LEVELS)}")
        return level

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"
