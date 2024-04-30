"""Telemetry configurations."""

from logging.config import dictConfig

from skbl.telemetry.request_filter import RequestInfoFilter
from skbl.telemetry.request_id import RequestIdFilter, request_id

__all__ = ["RequestIdFilter", "RequestInfoFilter", "configure_logging", "request_id"]


def configure_logging():
    """Configure logging."""
    log_config = {
        "version": 1,
        "filters": {
            "request_id": {
                "()": "skbl.telemetry.RequestIdFilter",
            },
            "request_info": {"()": "skbl.telemetry.RequestInfoFilter"},
        },
        "formatters": {
            "default": {
                "format": "[%(asctime)s] - %(name)s.%(module)s.%(funcName)s:%(lineno)d - %(levelname)s - %(remote_addr)s requested %(url)s - request_id=%(request_id)s - %(message)s",  # noqa: E501
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "filters": ["request_id", "request_info"],
                "formatter": "default",
            }
        },
        "loggers": {
            "skbl": {"level": "INFO", "handlers": ["wsgi"]},
            "werkzeug": {"level": "WARNING", "handlers": ["wsgi"]},
        },
    }
    dictConfig(log_config)

    # mail_handler.setFormatter(formatter)
