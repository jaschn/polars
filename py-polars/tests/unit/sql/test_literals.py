from __future__ import annotations

import pytest

import polars as pl
from polars.exceptions import SQLInterfaceError, SQLSyntaxError


def test_bit_hex_literals() -> None:
    with pl.SQLContext(df=None, eager=True) as ctx:
        out = ctx.execute(
            """
            SELECT *,
              -- bit strings
              b''                 AS b0,
              b'1001'             AS b1,
              b'11101011'         AS b2,
              b'1111110100110010' AS b3,
              -- hex strings
              x''                 AS x0,
              x'FF'               AS x1,
              x'4142'             AS x2,
              x'DeadBeef'         AS x3,
            FROM df
            """
        )

    assert out.to_dict(as_series=False) == {
        "b0": [b""],
        "b1": [b"\t"],
        "b2": [b"\xeb"],
        "b3": [b"\xfd2"],
        "x0": [b""],
        "x1": [b"\xff"],
        "x2": [b"AB"],
        "x3": [b"\xde\xad\xbe\xef"],
    }


def test_bit_hex_filter() -> None:
    df = pl.DataFrame(
        {"bin": [b"\x01", b"\x02", b"\x03", b"\x04"], "val": [9, 8, 7, 6]}
    )
    with pl.SQLContext(test=df) as ctx:
        for two in ("b'10'", "x'02'", "'\x02'", "b'0010'"):
            out = ctx.execute(f"SELECT val FROM test WHERE bin > {two}", eager=True)
            assert out.to_series().to_list() == [7, 6]


def test_bit_hex_errors() -> None:
    with pl.SQLContext(test=None) as ctx:
        with pytest.raises(
            SQLSyntaxError,
            match="bit string literal should contain only 0s and 1s",
        ):
            ctx.execute("SELECT b'007' FROM test", eager=True)

        with pytest.raises(
            SQLSyntaxError,
            match="hex string literal must have an even number of digits",
        ):
            ctx.execute("SELECT x'00F' FROM test", eager=True)

        with pytest.raises(
            SQLSyntaxError,
            match="hex string literal must have an even number of digits",
        ):
            pl.sql_expr("colx IN (x'FF',x'123')")

        with pytest.raises(
            SQLInterfaceError,
            match=r'NationalStringLiteral\("hmmm"\) is not supported',
        ):
            pl.sql_expr("N'hmmm'")


def test_bit_hex_membership() -> None:
    df = pl.DataFrame(
        {
            "x": [b"\x05", b"\xff", b"\xcc", b"\x0b"],
            "y": [1, 2, 3, 4],
        }
    )
    # this checks the internal `visit_any_value` codepath
    for values in (
        "b'0101', b'1011'",
        "x'05', x'0b'",
    ):
        dff = df.filter(pl.sql_expr(f"x IN ({values})"))
        assert dff["y"].to_list() == [1, 4]
