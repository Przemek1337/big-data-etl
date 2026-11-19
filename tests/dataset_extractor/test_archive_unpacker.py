import zipfile

from aml_etl.dataset_extractor.archive_unpacker import unpack_if_archive


def test_unpack_zip_returns_inner_csv(tmp_path):
    archive = tmp_path / "HI-Small_Trans.csv.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("HI-Small_Trans.csv", "a,b\n")
    result = unpack_if_archive(archive, tmp_path)
    assert result == tmp_path / "HI-Small_Trans.csv" and not archive.exists()
    assert result.read_text() == "a,b\n"


def test_plain_file_is_returned_unchanged(tmp_path):
    plain = tmp_path / "HI-Small_Trans.csv"
    plain.write_text("a,b\n")
    assert unpack_if_archive(plain, tmp_path) == plain
