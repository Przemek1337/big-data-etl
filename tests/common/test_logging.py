import logging

import pytest
from colorama import Fore, Style

from aml_etl.common.logging import ColorFormatter, configure_logging


@pytest.mark.parametrize(
    ("level", "color"),
    [
        (logging.DEBUG, Fore.CYAN),
        (logging.INFO, Fore.GREEN),
        (logging.WARNING, Fore.YELLOW),
        (logging.ERROR, Fore.RED),
        (logging.CRITICAL, Style.BRIGHT + Fore.RED),
    ],
)
def test_color_formatter_uses_level_color(level, color, monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    record = logging.LogRecord("svc", level, __file__, 1, "boom", None, None)
    output = ColorFormatter().format(record)
    assert color in output and "boom" in output and output.endswith(Style.RESET_ALL)


def test_no_color_env_disables_ansi(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    record = logging.LogRecord("svc", logging.ERROR, __file__, 1, "boom", None, None)
    assert "\x1b[" not in ColorFormatter().format(record)


def test_configure_logging_is_idempotent():
    configure_logging("DEBUG")
    configure_logging("DEBUG")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert [type(h.formatter) for h in root.handlers] == [ColorFormatter]
