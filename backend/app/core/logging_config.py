import logging

from pythonjsonlogger import jsonlogger


class MaskingJsonFormatter(jsonlogger.JsonFormatter):
    def process_log_record(self, log_record):
        sensitive_keys = {"password", "token", "secret", "authorization", "key"}
        for key in list(log_record.keys()):
            if any(sensitive_word in key.lower() for sensitive_word in sensitive_keys):
                log_record[key] = "***REDACTED***"
        return super().process_log_record(log_record)


def setup_logging():
    logger = logging.getLogger()

    # If the logger already has handlers, it might have been configured by uvicorn
    # or another library. We'll clear them to ensure our format takes precedence.
    if logger.hasHandlers():
        logger.handlers.clear()

    logHandler = logging.StreamHandler()

    # The format string dictates which standard LogRecord attributes are included in the JSON output
    formatter = MaskingJsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    logger.setLevel(logging.INFO)

    # Reduce noise from external libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return logger


logger = logging.getLogger(__name__)
