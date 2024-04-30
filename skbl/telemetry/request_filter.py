"""Request info."""

import logging

import flask


class RequestInfoFilter(logging.Filter):
    """Logging filter that makes the request url and remote_addr available for use in the logging format.

    Note that we're checking if we're in a request
    context, as we may want to log things before Flask is fully loaded.
    """  # noqa: E501

    def filter(self, record):  # noqa: PLR6301
        """Make the request url and remote_addr available for use in the logging format.

        Args:
            record (_type_): logging record

        Returns:
            bool: why?
        """
        have_request_context = flask.has_request_context()
        record.url = flask.request.url if have_request_context else ""
        record.remote_addr = flask.request.remote_addr if have_request_context else ""
        return True
