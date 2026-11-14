from support.raw_frames import raw_frame, raw_row

from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.transactions_etl.transaction_ids import add_transaction_ids


def test_id_is_variant_and_row_number():
    frame = raw_frame(raw_row(), raw_row())
    ids = add_transaction_ids(frame, DatasetVariant("HI-Small"))["_id"].to_list()
    assert ids == ["HI-Small:0", "HI-Small:1"]
    assert add_transaction_ids(frame, DatasetVariant("LI-Small"))["_id"][0] == "LI-Small:0"
