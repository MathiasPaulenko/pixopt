"""Tests for typed exceptions and structured logging."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from PIL import Image

from pixopt.bundle import generate_asset_bundle
from pixopt.exceptions import (
    BundleError,
    ConversionError,
    EXIFError,
    ImageNotFoundError,
    InvalidParameterError,
    OptimizationError,
    PipelineError,
    PixoptError,
    ResizeError,
    UnsupportedFormatError,
    WatermarkError,
)
from pixopt.logging import StructuredFormatter, configure_logging, get_logger
from pixopt.optimizer import optimize_image
from pixopt.pipeline import Pipeline


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_source(
    output_dir: Path, name: str = "source.jpg", size: tuple[int, int] = (200, 200)
) -> Path:
    path = output_dir / name
    Image.new("RGB", size, (100, 150, 200)).save(path, "JPEG", quality=90)
    return path


# ---------------------------------------------------------------------------
# Exception hierarchy tests
# ---------------------------------------------------------------------------


def test_pixopt_error_is_base() -> None:
    assert issubclass(ImageNotFoundError, PixoptError)
    assert issubclass(UnsupportedFormatError, PixoptError)
    assert issubclass(OptimizationError, PixoptError)
    assert issubclass(ConversionError, PixoptError)
    assert issubclass(ResizeError, PixoptError)
    assert issubclass(WatermarkError, PixoptError)
    assert issubclass(EXIFError, PixoptError)
    assert issubclass(PipelineError, PixoptError)
    assert issubclass(BundleError, PixoptError)
    assert issubclass(InvalidParameterError, PixoptError)


def test_pixopt_error_all_are_exceptions() -> None:
    assert issubclass(PixoptError, Exception)


def test_image_not_found_error() -> None:
    err = ImageNotFoundError("missing.jpg")
    assert "File not found" in str(err)
    assert err.path == Path("missing.jpg")


def test_image_not_found_error_raised_by_bundle(output_dir: Path) -> None:
    with pytest.raises(ImageNotFoundError):
        generate_asset_bundle("nonexistent.jpg", output_dir / "out")


def test_unsupported_format_error() -> None:
    err = UnsupportedFormatError("BMP")
    assert "Unsupported format" in str(err)
    assert err.fmt == "BMP"


def test_optimization_error() -> None:
    err = OptimizationError("Failed to save", path="img.jpg")
    assert "Failed to save" in str(err)
    assert "img.jpg" in str(err)


def test_conversion_error() -> None:
    err = ConversionError("Cannot convert")
    assert "Cannot convert" in str(err)


def test_resize_error() -> None:
    err = ResizeError("Invalid dimensions")
    assert "Invalid dimensions" in str(err)


def test_watermark_error() -> None:
    err = WatermarkError("Font not found")
    assert "Font not found" in str(err)


def test_exif_error() -> None:
    err = EXIFError("Corrupt EXIF")
    assert "Corrupt EXIF" in str(err)


def test_pipeline_error() -> None:
    err = PipelineError("No source")
    assert "No source" in str(err)


def test_bundle_error() -> None:
    err = BundleError("Failed to generate")
    assert "Failed to generate" in str(err)


def test_invalid_parameter_error() -> None:
    err = InvalidParameterError("quality must be 1-100")
    assert "quality must be 1-100" in str(err)


def test_pixopt_error_with_path() -> None:
    err = PixoptError("Something went wrong", path=Path("test.jpg"))
    assert "test.jpg" in str(err)
    assert err.path == Path("test.jpg")


def test_pixopt_error_without_path() -> None:
    err = PixoptError("Something went wrong")
    assert str(err) == "Something went wrong"
    assert err.path is None


# ---------------------------------------------------------------------------
# Logging tests
# ---------------------------------------------------------------------------


def test_get_logger_returns_logger() -> None:
    logger = get_logger("test")
    assert isinstance(logger, logging.Logger)
    assert "pixopt" in logger.name


def test_get_logger_has_null_handler_by_default() -> None:
    logger = get_logger("default_handler_test")
    assert any(isinstance(h, logging.NullHandler) for h in logger.handlers)


def test_configure_logging_adds_handler() -> None:
    import io

    stream = io.StringIO()
    logger = configure_logging(level="DEBUG", structured=False)
    # Replace the stream handler's stream with our StringIO
    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler):
            h.stream = stream

    logger.info("Test message")
    output = stream.getvalue()
    assert "Test message" in output
    assert "INFO" in output

    # Cleanup
    for h in list(logger.handlers):
        logger.removeHandler(h)
    logger.addHandler(logging.NullHandler())


def test_configure_logging_structured() -> None:
    import io

    stream = io.StringIO()
    logger = configure_logging(level="DEBUG", structured=True)
    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler):
            h.stream = stream

    logger.info("Structured test", extra={"operation": "test", "path": "img.jpg"})
    output = stream.getvalue().strip()
    parsed = json.loads(output)
    assert parsed["message"] == "Structured test"
    assert parsed["level"] == "INFO"
    assert parsed["operation"] == "test"
    assert parsed["path"] == "img.jpg"

    # Cleanup
    for h in list(logger.handlers):
        logger.removeHandler(h)
    logger.addHandler(logging.NullHandler())


def test_configure_logging_to_file(output_dir: Path) -> None:
    log_file = output_dir / "test.log"
    logger = configure_logging(level="DEBUG", structured=True, log_file=str(log_file))
    logger.info("File log test", extra={"operation": "file_test"})
    for h in list(logger.handlers):
        logger.removeHandler(h)
    logger.addHandler(logging.NullHandler())

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8").strip()
    parsed = json.loads(content)
    assert parsed["message"] == "File log test"


def test_structured_formatter_basic() -> None:
    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="pixopt.test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Hello %s",
        args=("world",),
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["message"] == "Hello world"
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "pixopt.test"


def test_structured_formatter_with_extras() -> None:
    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="pixopt.test",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg="Warning msg",
        args=(),
        exc_info=None,
    )
    record.operation = "optimize"
    record.path = "img.jpg"
    record.width = 800
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["operation"] == "optimize"
    assert parsed["path"] == "img.jpg"
    assert parsed["width"] == 800


def test_structured_formatter_with_exception() -> None:
    formatter = StructuredFormatter()
    try:
        raise ValueError("test error")
    except ValueError:
        import sys

        exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="pixopt.test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Failed",
            args=(),
            exc_info=exc_info,
        )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert "exception" in parsed
    assert "ValueError" in parsed["exception"]


def test_optimize_image_logs_not_found() -> None:
    import io

    stream = io.StringIO()
    logger = configure_logging(level="WARNING", structured=False)
    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler):
            h.stream = stream

    # This should log a warning about file not found
    result = optimize_image("nonexistent_file.jpg")
    assert not result.success
    output = stream.getvalue()
    assert "File not found" in output

    # Cleanup
    for h in list(logger.handlers):
        logger.removeHandler(h)
    logger.addHandler(logging.NullHandler())


def test_pipeline_logs_debug(output_dir: Path) -> None:
    import io

    source = _make_source(output_dir)
    stream = io.StringIO()
    logger = configure_logging(level="DEBUG", structured=False)
    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler):
            h.stream = stream

    output = output_dir / "logged.webp"
    result = Pipeline().open(source).save(output).run()
    assert result.output_path.exists()
    log_output = stream.getvalue()
    assert "Pipeline started" in log_output

    # Cleanup
    for h in list(logger.handlers):
        logger.removeHandler(h)
    logger.addHandler(logging.NullHandler())


def test_configure_logging_idempotent_no_duplicates() -> None:
    logger1 = configure_logging(level="INFO")
    handler_count_1 = len([h for h in logger1.handlers if not isinstance(h, logging.NullHandler)])
    logger2 = configure_logging(level="DEBUG")
    handler_count_2 = len([h for h in logger2.handlers if not isinstance(h, logging.NullHandler)])
    # Should not duplicate non-null handlers
    assert handler_count_2 == handler_count_1

    # Cleanup
    for h in list(logger2.handlers):
        logger2.removeHandler(h)
    logger2.addHandler(logging.NullHandler())
