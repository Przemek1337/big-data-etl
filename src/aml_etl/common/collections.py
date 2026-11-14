from enum import StrEnum


class LocalCollection(StrEnum):
    TRANSACTIONS = "transactions"
    IMPORT_RUNS = "import_runs"
    DATA_QUALITY = "data_quality"


class AtlasCollection(StrEnum):
    EXCHANGE_RATES = "exchange_rates"
    ANALYSIS_RESULTS = "analysis_results"
    DATASET_SUMMARY = "dataset_summary"
    DATASET_CATALOG = "dataset_catalog"
