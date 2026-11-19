import itertools

import pytest
from support.csv_rows import VALID, write_rows

from aml_etl.transactions_etl.csv_batch_reader import CsvBatchReader
from aml_etl.transactions_etl.transaction_schema import RAW_COLUMNS, UnexpectedHeaderError


def test_batches_have_contiguous_row_numbers(tmp_path):
    path = write_rows(tmp_path / "t.csv", [VALID] * 5)
    batches = list(CsvBatchReader(path, batch_rows=2).read_from())
    assert [b.frame.height for b in batches] == [2, 2, 1]
    assert [b.first_row_number for b in batches] == [0, 2, 4]
    assert all(a.next_row_number == b.first_row_number for a, b in itertools.pairwise(batches))
    assert batches[-1].next_row_number == 5


def test_resume_from_row_number_yields_remaining_rows(tmp_path):
    path = write_rows(tmp_path / "t.csv", [VALID] * 5)
    resumed = list(CsvBatchReader(path, batch_rows=2).read_from(2))
    assert [n for b in resumed for n in b.frame["row_number"].to_list()] == [2, 3, 4]


def test_resume_past_end_yields_nothing(tmp_path):
    path = write_rows(tmp_path / "t.csv", [VALID] * 2)
    assert list(CsvBatchReader(path, batch_rows=2).read_from(7)) == []


def test_ragged_line_is_counted_not_raised(tmp_path):
    path = write_rows(tmp_path / "t.csv", [VALID, "2022/09/01 00:20,010,8000EBD30", "", VALID])
    [batch] = list(CsvBatchReader(path, batch_rows=10).read_from())
    assert batch.frame.height == 2 and batch.malformed_line_count == 1
    assert batch.frame["row_number"].to_list() == [0, 3] and batch.next_row_number == 4


def test_batch_of_only_malformed_lines_has_empty_typed_frame(tmp_path):
    path = write_rows(tmp_path / "t.csv", ["x,y", "z"])
    [batch] = list(CsvBatchReader(path, batch_rows=10).read_from())
    assert batch.frame.height == 0 and batch.malformed_line_count == 2
    assert batch.frame.columns == [*RAW_COLUMNS, "row_number"]


def test_values_are_kept_as_strings(tmp_path):
    [batch] = list(
        CsvBatchReader(write_rows(tmp_path / "t.csv", [VALID]), batch_rows=10).read_from()
    )
    assert batch.frame.columns == [*RAW_COLUMNS, "row_number"]
    assert batch.frame["from_bank"].to_list() == ["010"]


def test_windows_line_endings_are_stripped(tmp_path):
    path = tmp_path / "t.csv"
    write_rows(path, [VALID])
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    [batch] = list(CsvBatchReader(path, batch_rows=10).read_from())
    assert batch.frame["is_laundering"].to_list() == ["0"]


def test_unexpected_header_raises(tmp_path):
    path = tmp_path / "t.csv"
    path.write_text("a,b,c\n1,2,3\n")
    with pytest.raises(UnexpectedHeaderError):
        list(CsvBatchReader(path, batch_rows=10).read_from())
