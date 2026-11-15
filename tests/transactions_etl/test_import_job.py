import logging

import pytest
from support.csv_rows import VALID, valid_row, write_rows
from support.import_jobs import (
    build_test_job,
    local_db,
    make_raw_dir,
    production_settings,
    seed_rates,
)

from aml_etl.transactions_etl.import_job import build_import_job
from aml_etl.transactions_etl.import_progress import ImportProgressTracker, ImportStatus

MIXED_ROWS = [
    VALID,
    VALID,
    valid_row(amount_paid="10"),
    valid_row(payment_currency="Zloty"),
    valid_row(amount_paid="11"),
    valid_row(amount_paid="12"),
    valid_row(amount_paid="13"),
]


def numbered_rows(count):
    return [valid_row(amount_paid=str(n)) for n in range(1, count + 1)]


def raw_file(tmp_path):
    return make_raw_dir(tmp_path) / "HI-Small_Trans.csv"


def tracker(settings):
    return ImportProgressTracker(local_db(settings)["import_runs"])


@pytest.mark.integration
def test_import_loads_valid_rows_and_rerun_adds_nothing(tmp_path, aml_settings):
    write_rows(raw_file(tmp_path), MIXED_ROWS)
    job = build_test_job(tmp_path, aml_settings, batch_rows=2)
    job.run()
    transactions = local_db(aml_settings)["transactions"]
    assert transactions.count_documents({}) == 6
    assert transactions.find_one({"_id": "HI-Small:0"})["amount_paid_usd"] == pytest.approx(3697.34)
    job.run()
    assert transactions.count_documents({}) == 6


@pytest.mark.integration
def test_indexes_are_created(tmp_path, aml_settings):
    write_rows(raw_file(tmp_path), [VALID])
    build_test_job(tmp_path, aml_settings, batch_rows=2).run()
    names = local_db(aml_settings)["transactions"].index_information()
    assert "dataset_variant_1_payment_format_1" in names
    assert "dataset_variant_1_from_account_1" in names


@pytest.mark.integration
def test_progress_and_quality_report_after_full_run(tmp_path, aml_settings, caplog):
    caplog.set_level(logging.INFO)
    write_rows(raw_file(tmp_path), MIXED_ROWS)
    job = build_test_job(tmp_path, aml_settings, batch_rows=2)
    job.run()
    progress = tracker(aml_settings).load("HI-Small")
    assert progress.status is ImportStatus.COMPLETED and progress.next_row_number == 7
    assert (progress.rows_read, progress.rows_inserted, progress.duplicate_rows) == (7, 6, 1)
    assert progress.rejections == {"unknown_currency": 1}
    quality = local_db(aml_settings)["data_quality"].find_one({"_id": "HI-Small"})
    assert (quality["rows_read"], quality["rows_loaded"], quality["rows_rejected"]) == (7, 6, 1)
    assert quality["exact_duplicate_rows"] == 1
    assert quality["rejection_rate"] == pytest.approx(1 / 7)
    assert quality["rejections"] == {"unknown_currency": 1} and quality["completed_at"]
    job.run()
    assert local_db(aml_settings)["transactions"].count_documents({}) == 6
    assert any("already imported" in r.getMessage() for r in caplog.records)


@pytest.mark.integration
def test_resumes_after_crash_without_duplicates(tmp_path, aml_settings):
    write_rows(raw_file(tmp_path), numbered_rows(6))
    with pytest.raises(RuntimeError):
        build_test_job(tmp_path, aml_settings, batch_rows=2, loader_fails_on_call=2).run()
    progress = tracker(aml_settings).load("HI-Small")
    assert progress.next_row_number == 2 and progress.status is ImportStatus.IN_PROGRESS
    build_test_job(tmp_path, aml_settings, batch_rows=2).run()
    assert local_db(aml_settings)["transactions"].count_documents({}) == 6
    final = tracker(aml_settings).load("HI-Small")
    assert (final.rows_read, final.rows_inserted, final.rows_already_present) == (6, 6, 0)
    assert final.status is ImportStatus.COMPLETED


@pytest.mark.integration
def test_batch_loaded_but_not_committed_is_not_duplicated(tmp_path, aml_settings):
    write_rows(raw_file(tmp_path), numbered_rows(6))
    with pytest.raises(RuntimeError):
        build_test_job(tmp_path, aml_settings, batch_rows=2, tracker_fails_on_save=2).run()
    assert local_db(aml_settings)["transactions"].count_documents({}) == 4
    build_test_job(tmp_path, aml_settings, batch_rows=2).run()
    assert local_db(aml_settings)["transactions"].count_documents({}) == 6
    final = tracker(aml_settings).load("HI-Small")
    assert (final.rows_read, final.rows_inserted, final.rows_already_present) == (6, 4, 2)


@pytest.mark.integration
def test_changed_source_file_restarts_from_row_zero(tmp_path, aml_settings, caplog):
    write_rows(raw_file(tmp_path), numbered_rows(1))
    build_test_job(tmp_path, aml_settings, batch_rows=2).run()
    write_rows(raw_file(tmp_path), numbered_rows(2))
    build_test_job(tmp_path, aml_settings, batch_rows=2).run()
    assert local_db(aml_settings)["transactions"].count_documents({}) == 2
    assert any(r.levelno == logging.WARNING for r in caplog.records)
    assert tracker(aml_settings).load("HI-Small").rows_read == 2


@pytest.mark.integration
def test_malformed_lines_and_missing_rates_are_reported(tmp_path, aml_settings):
    rows = [VALID, "broken,line", valid_row(timestamp="2022/09/05 10:00"), VALID]
    write_rows(raw_file(tmp_path), rows)
    build_test_job(tmp_path, aml_settings, batch_rows=10).run()
    progress = tracker(aml_settings).load("HI-Small")
    assert progress.rejections == {"malformed_line": 1, "missing_exchange_rate": 1}
    assert (progress.rows_read, progress.rows_inserted) == (4, 2)


@pytest.mark.integration
def test_production_builder_wires_progress_and_quality(tmp_path, aml_settings):
    write_rows(raw_file(tmp_path), [VALID])
    seed_rates(aml_settings)
    build_import_job(production_settings(tmp_path, aml_settings, batch_rows=2)).run()
    assert tracker(aml_settings).load("HI-Small").status is ImportStatus.COMPLETED
    assert local_db(aml_settings)["data_quality"].count_documents({}) == 1
