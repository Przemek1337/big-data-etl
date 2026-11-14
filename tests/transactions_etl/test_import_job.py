import pytest
from support.csv_rows import VALID, valid_row, write_rows
from support.import_jobs import build_test_job, local_db, make_raw_dir


@pytest.mark.integration
def test_import_loads_valid_rows_and_rerun_adds_nothing(tmp_path, aml_settings):
    rows = [
        VALID,
        VALID,
        valid_row(amount_paid="10"),
        valid_row(payment_currency="Zloty"),
        valid_row(amount_paid="11"),
        valid_row(amount_paid="12"),
        valid_row(amount_paid="13"),
    ]
    write_rows(make_raw_dir(tmp_path) / "HI-Small_Trans.csv", rows)
    job = build_test_job(tmp_path, aml_settings, batch_rows=2)
    job.run()
    transactions = local_db(aml_settings)["transactions"]
    assert transactions.count_documents({}) == 6
    assert transactions.find_one({"_id": "HI-Small:0"})["amount_paid_usd"] == pytest.approx(3697.34)
    job.run()
    assert transactions.count_documents({}) == 6


@pytest.mark.integration
def test_indexes_are_created(tmp_path, aml_settings):
    write_rows(make_raw_dir(tmp_path) / "HI-Small_Trans.csv", [VALID])
    build_test_job(tmp_path, aml_settings, batch_rows=2).run()
    names = local_db(aml_settings)["transactions"].index_information()
    assert "dataset_variant_1_payment_format_1" in names
    assert "dataset_variant_1_from_account_1" in names
