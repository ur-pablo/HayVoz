import logging

from app.logging_config import JsonFormatter
from app.privacy import redact_text


def test_redaction_removes_common_secret_forms() -> None:
    value = (
        "Authorization: Bearer top-secret token=my-token "
        "api_key=another-secret sk-abcdefgh12345678"
    )
    redacted = redact_text(value)
    assert "top-secret" not in redacted
    assert "my-token" not in redacted
    assert "another-secret" not in redacted
    assert "sk-abcdefgh12345678" not in redacted
    assert redacted.count("[REDACTED]") == 4


def test_json_formatter_redacts_log_messages() -> None:
    record = logging.LogRecord(
        "hayvoz.test",
        logging.INFO,
        __file__,
        1,
        "password=%s",
        ("do-not-log",),
        None,
    )
    output = JsonFormatter().format(record)
    assert "do-not-log" not in output
    assert "[REDACTED]" in output
