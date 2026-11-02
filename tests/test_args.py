"""Ported from gangtise-openapi-cli tests/unit/args.test.ts (numbers) plus CLI wiring."""
import pytest

from gangtise_core.args import parse_from, parse_number_option, parse_size
from gangtise_core.errors import ValidationError


def test_parses_finite_numbers():
    assert parse_number_option("12.5", "--x") == 12.5
    assert parse_number_option("7", "--x", integer=True) == 7
    assert parse_number_option(3, "--x", integer=True) == 3


@pytest.mark.parametrize("value", ["inf", "nan", "", "  ", None])
def test_rejects_non_finite_or_empty(value):
    with pytest.raises(ValidationError):
        parse_number_option(value, "--x")


def test_enforces_integer_and_minimum():
    with pytest.raises(ValidationError, match="integer"):
        parse_number_option("1.5", "--size", integer=True)
    with pytest.raises(ValidationError, match=">= 1"):
        parse_number_option("0", "--size", integer=True, min=1)


@pytest.mark.parametrize("value", ["0x10", "1e3", "5.0", "1_000", "１２", "+5"])
def test_plain_decimal_only(value):
    with pytest.raises(ValidationError, match="plain decimal"):
        parse_number_option(value, "--size", integer=True)


def test_refuses_integer_past_safe_range():
    with pytest.raises(ValidationError):
        parse_number_option(str(2**53), "--from", integer=True)


def test_pagination_helpers():
    assert parse_from(None) == 0
    assert parse_from("20") == 20
    assert parse_size(None) is None
    assert parse_size("50") == 50
    with pytest.raises(ValidationError):
        parse_from("-1")
    with pytest.raises(ValidationError):
        parse_size("0")


# ── CLI argparse wiring ──

@pytest.fixture()
def cli_main(monkeypatch):
    import importlib
    from pathlib import Path

    from gangtise_core import handlers_catalog

    root = Path(__file__).resolve().parents[1]
    handlers_catalog.load_catalog(force=True, generated_root=root / "cli" / "src" / "_generated")
    cli = importlib.import_module("gangtise_cli.main")

    monkeypatch.setattr(cli, "_check_auth_configured", lambda: None)
    return cli


def _run(cli, argv):
    with pytest.raises(SystemExit) as ei:
        cli.main(argv)
    return ei.value.code


@pytest.mark.parametrize(
    "argv,needle",
    [
        (["quote", "--securities", "600519.SH", "--limit", "0x10"], "plain decimal"),
        (["quote", "--securities", "600519.SH", "--limit", "0"], ">= 1"),
        (["quote", "--securities", "600519.SH", "--start-date", "07/01/2026"], "year-last"),
        (["quote", "--securities", "600519.SH", "--start-date", "2026-02-30"], "not a real calendar date"),
        (["private-record", "--start-time", "01-07-2026 09:00"], "year-last"),
    ],
)
def test_cli_refuses_bad_values_with_exit_2(cli_main, capsys, argv, needle):
    assert _run(cli_main, argv) == 2
    assert needle in capsys.readouterr().err


def test_cli_normalizes_year_first_dates_before_the_handler(cli_main, monkeypatch):
    seen = {}

    def fake_invoke(handler, kwargs, *, tool=""):
        seen.update(kwargs)
        from gangtise_core.result import Result

        return Result.success(text="ok", tool=tool)

    monkeypatch.setattr(cli_main, "invoke_legacy", fake_invoke)
    code = _run(
        cli_main,
        ["quote", "--securities", "600519.SH", "--start-date", "2026/07/01", "--end-date", "20260705", "--limit", "10"],
    )
    assert code == 0
    assert seen["start_date"] == "2026-07-01"
    assert seen["end_date"] == "2026-07-05"
    assert seen["limit"] == 10


def test_cli_keeps_exit_code_when_reader_goes_away(cli_main, monkeypatch):
    from gangtise_core.errors import PartialResultError
    from gangtise_core.result import Result

    monkeypatch.setattr(
        cli_main,
        "invoke_legacy",
        lambda handler, kwargs, *, tool="": Result.from_error(PartialResultError("部分失败")),
    )

    def broken(*_a, **_k):
        raise BrokenPipeError

    monkeypatch.setattr(cli_main, "emit_cli", broken)
    monkeypatch.setattr(cli_main, "_silence_stdout", lambda: None)
    assert _run(cli_main, ["quote", "--securities", "600519.SH"]) == 3


def test_ctrl_c_exits_130(cli_main, monkeypatch):
    def interrupted(_argv=None):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli_main, "main", interrupted)
    with pytest.raises(SystemExit) as ei:
        cli_main.run([])
    assert ei.value.code == 130
