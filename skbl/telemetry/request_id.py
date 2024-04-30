"""Request ids."""

import logging
import uuid

import flask


def generate_request_id(original_id: str | None) -> str:
    """Generate a new request ID, optionally including an original request ID.

    Args:
        original_id (str, optional): original id. Defaults to "".

    Returns:
        str: a request id
    """
    new_id = uuid.uuid4()

    return f"{original_id},{new_id}" if original_id else str(new_id)


def request_id() -> str:
    """Return the current request ID or a new one if there is none.

    In order of preference:
    * If we've already created a request ID and stored it in the flask.g context local, use that
    * If a client has passed in the X-Request-Id header, create a new ID with that prepended
    * Otherwise, generate a request ID and store it in flask.g.request_id

    Returns:
        str | None: _description_
    """
    if getattr(flask.g, "request_id", None):
        return flask.g.request_id

    headers = flask.request.headers
    original_request_id = headers.get("X-Request-Id")
    new_uuid = generate_request_id(original_request_id)
    flask.g.request_id = new_uuid

    return new_uuid


class RequestIdFilter(logging.Filter):
    """Logging filter that makes the request ID available for use in the logging format.

    Note that we're checking if we're in a request
    context, as we may want to log things before Flask is fully loaded.
    """

    def filter(self, record):  # noqa: PLR6301
        """Make the request ID available for use in the logging format.

        Args:
            record (_type_): logging record

        Returns:
            bool: why?
        """
        record.request_id = request_id() if flask.has_request_context() else ""
        return True
