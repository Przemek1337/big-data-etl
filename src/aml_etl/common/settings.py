from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from aml_etl.common.dataset_variants import DatasetVariant


def _default_variants() -> list[DatasetVariant]:
    return [DatasetVariant("HI-Medium"), DatasetVariant("LI-Medium")]


class AmlSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    log_level: str = "INFO"
    local_mongo_uri: str = "mongodb://localhost:27018"
    local_database: str = "aml"
    atlas_uri: str = "mongodb://localhost:27018"
    atlas_database: str = "aml_results"
    mongo_timeout_ms: int = 10_000
    dataset_variants: Annotated[list[DatasetVariant], NoDecode] = _default_variants()
    data_dir: Path = Path("data")
    kaggle_dataset: str = "ealtman2019/ibm-transactions-for-anti-money-laundering-aml"
    csv_batch_rows: int = 250_000

    @field_validator("dataset_variants", mode="before")
    @classmethod
    def _split_variants(cls, value: object) -> object:
        if isinstance(value, str):
            names = [name.strip() for name in value.split(",") if name.strip()]
            return [DatasetVariant(name) for name in names]
        return value

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"
