from support.fake_downloader import FakeDownloader

from aml_etl.common.dataset_variants import DatasetVariant
from aml_etl.dataset_extractor.raw_dataset_extractor import RawDatasetExtractor


def test_downloads_once_and_skips_on_rerun(tmp_path):
    downloader = FakeDownloader()
    extractor = RawDatasetExtractor(downloader, tmp_path, [DatasetVariant("HI-Small")])
    first, second = list(extractor.extract()), list(extractor.extract())
    assert downloader.calls == ["HI-Small_Trans.csv"]
    assert first == second == [tmp_path / "HI-Small_Trans.csv"]


def test_redownloads_when_marker_missing(tmp_path):
    (tmp_path / "HI-Small_Trans.csv").write_text("partial")
    downloader = FakeDownloader()
    list(RawDatasetExtractor(downloader, tmp_path, [DatasetVariant("HI-Small")]).extract())
    assert downloader.calls == ["HI-Small_Trans.csv"]
    assert (tmp_path / "HI-Small_Trans.csv").read_bytes() == b"header\nrow\n"


def test_creates_missing_raw_directory(tmp_path):
    raw_dir = tmp_path / "data" / "raw"
    paths = list(
        RawDatasetExtractor(FakeDownloader(), raw_dir, [DatasetVariant("LI-Small")]).extract()
    )
    assert paths == [raw_dir / "LI-Small_Trans.csv"]
    assert (raw_dir / "LI-Small_Trans.csv.complete").exists()
