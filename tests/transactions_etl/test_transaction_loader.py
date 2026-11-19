import pytest
from pymongo.errors import BulkWriteError
from support.import_jobs import enriched_frame

from aml_etl.transactions_etl.transaction_loader import LoadResult, TransactionLoader


@pytest.mark.integration
def test_loader_reports_already_present_on_reload(mongo_database):
    loader = TransactionLoader(mongo_database["transactions"])
    frame = enriched_frame(3)
    assert loader.load(frame) == LoadResult(inserted=3, already_present=0)
    assert loader.load(frame) == LoadResult(inserted=0, already_present=3)
    assert mongo_database["transactions"].count_documents({}) == 3


@pytest.mark.integration
def test_loader_keeps_timestamps_timezone_aware(mongo_database):
    TransactionLoader(mongo_database["transactions"]).load(enriched_frame(1))
    stored = mongo_database["transactions"].find_one({"_id": "HI-Small:0"})
    assert stored["timestamp"].utcoffset().total_seconds() == 0
    assert stored["is_cross_currency"] is False and stored["row_number"] == 0


@pytest.mark.integration
def test_loader_reraises_non_duplicate_errors(mongo_database):
    mongo_database.create_collection(
        "strict", validator={"$jsonSchema": {"required": ["never_present"]}}
    )
    with pytest.raises(BulkWriteError):
        TransactionLoader(mongo_database["strict"]).load(enriched_frame(2))


def test_empty_frame_does_not_touch_database():
    assert TransactionLoader(None).load(enriched_frame(0)) == LoadResult(0, 0)


@pytest.mark.integration
def test_reloading_a_full_import_batch_of_duplicates_does_not_overflow_reply(mongo_database):
    loader = TransactionLoader(mongo_database["transactions"])
    frame = enriched_frame(250_000)
    assert loader.load(frame) == LoadResult(inserted=250_000, already_present=0)
    assert loader.load(frame) == LoadResult(inserted=0, already_present=250_000)


@pytest.mark.integration
def test_partially_present_batch_is_split_across_chunks(mongo_database):
    loader = TransactionLoader(mongo_database["transactions"], chunk_rows=2)
    loader.load(enriched_frame(3))
    assert loader.load(enriched_frame(5)) == LoadResult(inserted=2, already_present=3)
    assert mongo_database["transactions"].count_documents({}) == 5
