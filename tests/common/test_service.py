import logging

from aml_etl.common.service import run_service
from aml_etl.common.settings import AmlSettings


class OkJob:
    def run(self) -> None:
        return None


class FailingJob:
    def run(self) -> None:
        raise RuntimeError("boom")


def test_successful_job_returns_zero(caplog):
    assert run_service("svc", lambda s: OkJob(), settings=AmlSettings(_env_file=None)) == 0


def test_failing_job_returns_exit_code_one(caplog):
    code = run_service("svc", lambda s: FailingJob(), settings=AmlSettings(_env_file=None))
    assert code == 1
    assert any(r.levelno == logging.ERROR and "svc" in r.getMessage() for r in caplog.records)


def test_failing_job_builder_returns_exit_code_one(caplog):
    def build(settings: AmlSettings) -> OkJob:
        raise RuntimeError("cannot build")

    assert run_service("svc", build, settings=AmlSettings(_env_file=None)) == 1


def test_failure_is_one_readable_line_without_traceback_at_info_level(caplog):
    settings = AmlSettings(_env_file=None, log_level="INFO")
    run_service("svc", lambda s: FailingJob(), settings=settings)
    [record] = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert record.getMessage() == "svc failed: RuntimeError: boom"
    assert not record.exc_info


def test_failure_keeps_traceback_at_debug_level(caplog):
    settings = AmlSettings(_env_file=None, log_level="DEBUG")
    run_service("svc", lambda s: FailingJob(), settings=settings)
    [record] = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert record.exc_info
