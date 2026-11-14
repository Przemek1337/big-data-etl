import logging

from support.fake_downloader import FakeDownloader

from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.dataset_extractor.extraction_job import ExtractionJob
from aml_etl.dataset_extractor.raw_dataset_extractor import RawDatasetExtractor


def test_job_warns_below_threshold(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    job = ExtractionJob(
        RawDatasetExtractor(FakeDownloader(), tmp_path, [DatasetVariant("HI-Small")])
    )
    job.run()
    assert any(r.levelno == logging.WARNING and "5 GB" in r.getMessage() for r in caplog.records)


def test_job_does_not_warn_at_threshold(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    extractor = RawDatasetExtractor(FakeDownloader(), tmp_path, [DatasetVariant("HI-Small")])
    ExtractionJob(extractor, minimum_total_bytes=11).run()
    assert not any(r.levelno == logging.WARNING for r in caplog.records)
