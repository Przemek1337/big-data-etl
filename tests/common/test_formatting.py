from aml_etl.common.formatting import (
    format_compact,
    format_count,
    format_decimal,
    format_percent,
    format_usd,
)


def test_polish_formatting():
    assert format_count(35230) == "35 230"
    assert format_usd(1240.4) == "$1 240"
    assert format_decimal(3.14) == "3,1"
    assert format_percent(0.0011) == "0,11%"
    assert format_compact(31_860_000) == "31,86 mln"
    assert format_compact(4_200_000_000_000) == "4,2 bln"
    assert format_compact(950) == "950"


def test_compact_thresholds():
    assert format_compact(1_500) == "1,5 tys."
    assert format_compact(2_000_000_000) == "2 mld"
