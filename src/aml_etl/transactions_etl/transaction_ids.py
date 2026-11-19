import polars as pl

from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.transactions_etl.transaction_schema import ROW_NUMBER_COLUMN

ID_COLUMN = "_id"


def add_transaction_ids(frame: pl.DataFrame, variant: DatasetVariant) -> pl.DataFrame:
    return frame.with_columns(
        pl.format("{}:{}", pl.lit(variant.name), pl.col(ROW_NUMBER_COLUMN)).alias(ID_COLUMN)
    )
